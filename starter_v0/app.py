"""Streamlit UI for the research agent live demo.

Reuses run_model_tool_loop() from chat.py so the UI and the CLI share one agent
loop, and writes the same transcript format to transcripts/.

Two modes:
  - Chat      — live multi-turn demo against the current artifacts.
  - So sánh   — one scenario run across several artifact versions side by side,
                so the demo shows what each version actually changed.
"""
from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    ARTIFACTS_DIR,
    ROOT,
    json_text,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

PROVIDERS = ["openrouter", "openai", "anthropic", "gemini"]
TRANSCRIPTS_DIR = ROOT / "transcripts"
VERSIONS_DIR = ARTIFACTS_DIR / "versions"
VERSION_LOG = ARTIFACTS_DIR / "version_log.csv"

STATUS_STYLE = {
    "answered": ("✅", "Trả lời xong"),
    "waiting_for_user": ("❓", "Đang chờ người dùng bổ sung"),
    "max_tool_rounds": ("⚠️", "Dừng vì chạm giới hạn tool rounds"),
    "provider_error": ("🛑", "Lỗi provider"),
}


st.set_page_config(page_title="Research Agent — Live Demo", page_icon="🔎", layout="wide")


@st.cache_resource(show_spinner=False)
def get_provider(name: str) -> Any:
    return make_provider(name)


def provider_default_model(name: str) -> str | None:
    """Missing API key must not kill the app before the user can switch provider."""
    try:
        return getattr(get_provider(name), "default_model", None)
    except Exception:
        return None


# ---------------- Artifact versions ----------------

def discover_versions() -> dict[str, dict[str, Path]]:
    """Version snapshots live in artifacts/versions/<label>/{system_prompt.md,tools.yaml}."""
    found: dict[str, dict[str, Path]] = {}
    if VERSIONS_DIR.is_dir():
        for directory in sorted(VERSIONS_DIR.iterdir()):
            prompt_path = directory / "system_prompt.md"
            tools_path = directory / "tools.yaml"
            if prompt_path.exists() and tools_path.exists():
                found[directory.name] = {"system_prompt": prompt_path, "tools": tools_path}
    return found


def logged_hashes() -> dict[str, tuple[str, str]]:
    if not VERSION_LOG.exists():
        return {}
    with VERSION_LOG.open(encoding="utf-8") as handle:
        return {
            row["version"].strip(): (row["prompt_hash"].strip(), row["tools_hash"].strip())
            for row in csv.DictReader(handle)
            if row.get("version")
        }


def verify_against_log(label: str, prompt_path: Path, tools_path: Path) -> tuple[Any, bool | None]:
    """Return (ArtifactVersion, matches_version_log). None = label absent from the log."""
    artifact_version = build_artifact_version(label, prompt_path, tools_path)
    expected = logged_hashes().get(label)
    if expected is None:
        return artifact_version, None
    actual = (f"p{artifact_version.prompt_hash[:12]}", f"t{artifact_version.tools_hash[:12]}")
    return artifact_version, actual == expected


def load_artifacts(prompt_path: Path, tools_path: Path) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    system_prompt = prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    return system_prompt, declarations, to_openai_tools(declarations)


def hash_badge(matches: bool | None) -> None:
    if matches is True:
        st.success("Khớp hash trong version_log.csv", icon="🔒")
    elif matches is False:
        st.warning("KHÔNG khớp hash trong version_log.csv", icon="⚠️")
    else:
        st.info("Chưa có dòng nào trong version_log.csv", icon="ℹ️")


# ---------------- Transcript ----------------

def new_transcript(config: dict[str, Any], artifact_version: Any, prompt_path: Path, tools_path: Path) -> tuple[dict[str, Any], Path]:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(artifact_version.version), safe_slug(config["provider"]), timestamp])
    transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": config["provider"],
        "model": config["model"] or provider_default_model(config["provider"]),
        "system_prompt": str(prompt_path),
        "tools": str(tools_path),
        "history_window": config["history_window"],
        "max_tool_rounds": config["max_tool_rounds"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    return transcript, TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"


def reset_session(config: dict[str, Any], artifact_version: Any, prompt_path: Path, tools_path: Path) -> None:
    transcript, path = new_transcript(config, artifact_version, prompt_path, tools_path)
    st.session_state.transcript = transcript
    st.session_state.transcript_path = path
    st.session_state.history = []
    st.session_state.turns = []
    st.session_state.turn_index = 0


# ---------------- Trace rendering ----------------

def tool_status(result: Any) -> tuple[str, str | None]:
    """README requires per-tool status and result/error to be visible."""
    if isinstance(result, dict):
        if result.get("error"):
            return "❌", f"{result.get('error')}: {result.get('message', '')}".strip(": ")
        if result.get("awaiting_user"):
            return "❓", "awaiting_user"
        if result.get("status"):
            return "⏸️", str(result.get("status"))
    return "✅", None


def render_rounds(rounds: list[dict[str, Any]], *, compact: bool = False) -> None:
    """Show every tool call with its round, args, status and result/error."""
    for record in rounds:
        calls = record.get("tool_calls") or []
        if not calls:
            continue
        names = ", ".join(call["name"] for call in calls)
        label = f"🔧 Round {record['round']} — {len(calls)} tool call(s): {names}"
        with st.expander(label, expanded=True):
            if record.get("assistant_text") and not compact:
                st.caption(record["assistant_text"])
            results = record.get("tool_results") or []
            for index, call in enumerate(calls):
                result = results[index].get("result") if index < len(results) else None
                icon, detail = tool_status(result)
                st.markdown(f"{icon} **{call['name']}**" + (f" — `{detail}`" if detail else ""))
                st.code(json_text(call["args"]), language="json")
                if index < len(results):
                    with st.popover("Result", use_container_width=True):
                        st.code(json_text(result, max_chars=6000), language="json")


def render_outcome(turn: dict[str, Any]) -> None:
    status = turn.get("status", "answered")
    icon, caption = STATUS_STYLE.get(status, ("•", status))
    if status == "provider_error":
        st.error(turn.get("error", "Unknown provider error"))
    elif status == "waiting_for_user":
        st.info(turn.get("assistant_text") or "")
    else:
        st.markdown(turn.get("assistant_text") or "")
    st.caption(f"{icon} {caption} · {len(turn.get('tool_events') or [])} tool event(s)")


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.markdown(turn["user"])
    with st.chat_message("assistant"):
        render_rounds(turn.get("rounds") or [])
        render_outcome(turn)


def execute_turn(
    *,
    provider_name: str,
    model: str,
    system_prompt: str,
    openai_tools: list[dict[str, Any]],
    max_tool_rounds: int,
    messages: list[dict[str, str]],
    user_text: str,
    turn_index: int,
) -> dict[str, Any]:
    """One turn through the shared agent loop, in transcript-turn shape."""
    turn_record: dict[str, Any] = {
        "turn_index": turn_index,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    try:
        turn_record.update(
            run_model_tool_loop(
                provider=get_provider(provider_name),
                messages=messages,
                tools=openai_tools,
                model=model or None,
                max_tool_rounds=max_tool_rounds,
            )
        )
    except Exception as exc:
        turn_record.update({"status": "provider_error", "error": f"{type(exc).__name__}: {exc}"})
    turn_record["ended_at"] = now_iso()
    return turn_record


# ---------------- Sidebar ----------------

versions = discover_versions()

with st.sidebar:
    st.header("Cấu hình")
    mode = st.radio("Chế độ", ["Chat", "So sánh version"], horizontal=True)
    provider_name = st.selectbox("Provider", PROVIDERS, index=0)
    model = st.text_input("Model", value="", placeholder="để trống = default của provider").strip()
    max_tool_rounds = st.slider("Max tool rounds", 1, 8, 4)
    history_window = st.slider("History window (số cặp lượt)", 1, 15, 5)

    st.divider()
    st.caption("Artifacts đang chạy (Chat)")
    version = st.text_input("Version label", value="v4").strip() or "v4"
    system_prompt_path = Path(st.text_input("System prompt", value=str(ARTIFACTS_DIR / "system_prompt.md")))
    tools_path = Path(st.text_input("Tools", value=str(ARTIFACTS_DIR / "tools.yaml")))

if not system_prompt_path.exists() or not tools_path.exists():
    st.error(f"Không tìm thấy artifact: {system_prompt_path if not system_prompt_path.exists() else tools_path}")
    st.stop()

# Reloaded every rerun so edits to the artifacts show up without restarting.
system_prompt, tool_declarations, openai_tools = load_artifacts(system_prompt_path, tools_path)
artifact_version, matches_log = verify_against_log(version, system_prompt_path, tools_path)

config = {
    "provider": provider_name,
    "model": model,
    "history_window": history_window,
    "max_tool_rounds": max_tool_rounds,
}
signature = (provider_name, model, artifact_version.artifact_version)

if "transcript" not in st.session_state or st.session_state.get("signature") != signature:
    reset_session(config, artifact_version, system_prompt_path, tools_path)
    st.session_state.signature = signature

with st.sidebar:
    st.code(artifact_version.artifact_version, language=None)
    hash_badge(matches_log)
    with st.expander(f"{len(tool_declarations)} tool đã nạp"):
        for declaration in tool_declarations:
            st.markdown(f"**{declaration['name']}** — {declaration.get('description', '')}")
    with st.expander("System prompt"):
        st.code(system_prompt, language="markdown")

    if st.button(f"📌 Lưu snapshot `{version}`", use_container_width=True):
        target = VERSIONS_DIR / safe_slug(version)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(system_prompt_path, target / "system_prompt.md")
        shutil.copy2(tools_path, target / "tools.yaml")
        st.success(f"Đã lưu {target.relative_to(ROOT)}")
        st.rerun()

    st.divider()
    st.caption("Transcript")
    st.code(str(st.session_state.transcript_path.relative_to(ROOT)), language=None)
    st.download_button(
        "Tải transcript",
        data=json_text(st.session_state.transcript),
        file_name=st.session_state.transcript_path.name,
        mime="application/json",
        use_container_width=True,
    )
    if st.button("Phiên mới", use_container_width=True):
        reset_session(config, artifact_version, system_prompt_path, tools_path)
        st.rerun()


# ---------------- Mode: compare versions ----------------

if mode == "So sánh version":
    st.title("🆚 So sánh version")
    st.caption("Cùng một scenario chạy qua nhiều artifact version để thấy version nào cải thiện gì.")

    if len(versions) < 2:
        st.warning(
            f"Cần ít nhất 2 snapshot trong `{VERSIONS_DIR.relative_to(ROOT)}/`. "
            "Dùng nút **Lưu snapshot** ở sidebar để lưu artifacts hiện tại dưới một version label."
        )
        st.stop()

    labels = list(versions)
    selected = st.multiselect(
        "Version cần so sánh",
        labels,
        default=labels[:2] if len(labels) >= 2 else labels,
    )
    scenario = st.text_input(
        "Scenario",
        value="Tóm tắt 5 tweet mới nhất giúp mình",
        help="Một request duy nhất, chạy y hệt nhau trên mọi version đã chọn.",
    )
    run_compare = st.button("▶️ Chạy trên tất cả version", type="primary", disabled=not selected or not scenario.strip())

    if run_compare:
        outcomes: list[dict[str, Any]] = []
        progress = st.progress(0.0, text="Đang chạy…")
        for index, label in enumerate(selected, start=1):
            paths = versions[label]
            version_prompt, _, version_tools = load_artifacts(paths["system_prompt"], paths["tools"])
            version_artifact, version_match = verify_against_log(label, paths["system_prompt"], paths["tools"])
            progress.progress(index / len(selected), text=f"{label} — {version_artifact.artifact_version}")

            turn = execute_turn(
                provider_name=provider_name,
                model=model,
                system_prompt=version_prompt,
                openai_tools=version_tools,
                max_tool_rounds=max_tool_rounds,
                messages=[
                    {"role": "system", "content": version_prompt},
                    {"role": "user", "content": scenario},
                ],
                user_text=scenario,
                turn_index=1,
            )

            transcript, path = new_transcript(config, version_artifact, paths["system_prompt"], paths["tools"])
            transcript["turns"].append(turn)
            write_transcript(path, transcript)

            outcomes.append({
                "label": label,
                "artifact_version": version_artifact.artifact_version,
                "matches_log": version_match,
                "turn": turn,
                "transcript_path": path,
            })
        progress.empty()
        st.session_state.compare = {"scenario": scenario, "outcomes": outcomes}

    comparison = st.session_state.get("compare")
    if comparison:
        st.divider()
        st.markdown(f"**Scenario:** {comparison['scenario']}")
        columns = st.columns(len(comparison["outcomes"]))
        for column, outcome in zip(columns, comparison["outcomes"]):
            with column:
                st.subheader(outcome["label"])
                st.code(outcome["artifact_version"], language=None)
                hash_badge(outcome["matches_log"])
                calls = [
                    call["name"]
                    for record in outcome["turn"].get("rounds") or []
                    for call in record.get("tool_calls") or []
                ]
                st.metric("Tool calls", len(calls), delta=", ".join(calls) or "không gọi tool", delta_color="off")
                render_rounds(outcome["turn"].get("rounds") or [], compact=True)
                render_outcome(outcome["turn"])
                st.caption(f"📄 {outcome['transcript_path'].relative_to(ROOT)}")
    st.stop()


# ---------------- Mode: chat ----------------

st.title("🔎 Research Agent")
st.caption(f"{provider_name} · {model or 'default model'} · {artifact_version.artifact_version}")

for turn in st.session_state.turns:
    render_turn(turn)

if user_text := st.chat_input("Hỏi gì đó, ví dụ: Tin AI hôm nay có gì nổi bật?"):
    with st.chat_message("user"):
        st.markdown(user_text)

    st.session_state.turn_index += 1
    with st.chat_message("assistant"):
        with st.spinner("Agent đang chạy…"):
            turn_record = execute_turn(
                provider_name=provider_name,
                model=model,
                system_prompt=system_prompt,
                openai_tools=openai_tools,
                max_tool_rounds=max_tool_rounds,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *trim_history(st.session_state.history, history_window),
                    {"role": "user", "content": user_text},
                ],
                user_text=user_text,
                turn_index=st.session_state.turn_index,
            )
        if turn_record["status"] != "provider_error":
            st.session_state.history.append({"role": "user", "content": user_text})
            st.session_state.history.append({"role": "assistant", "content": turn_record["assistant_text"]})
        render_rounds(turn_record.get("rounds") or [])
        render_outcome(turn_record)

    st.session_state.turns.append(turn_record)
    st.session_state.transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, st.session_state.transcript)
