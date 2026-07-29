# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v4, failure, eval, chat) dựa trên log thật.

## Team

- Team: K3 — G28
- Members:
`Đặng Thái Nam Sơn` 2A202601431
`Chu Thành Dũng` 2A202601405
`Trần Đình Đăng` 2A202601998
`Cao Nam Cường` 2A202601661
`Dương Mạnh Phong` 2A202601557
- Provider/model: `openrouter` / `openai/gpt-4o-mini`
- Ngày thực hiện: 2026-07-29

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent tiếng Việt: tìm tin trên web theo từ khóa, lấy bài đăng gần đây của một tài khoản mạng xã hội, tìm bài báo khoa học trên arXiv, đọc nội dung một URL, rồi tổng hợp thành digest. Agent **hỏi lại khi thiếu thông tin bắt buộc** và **xin xác nhận trước khi đăng/gửi ra ngoài**.

**Link dùng thử (truy cập được trong showdown):**

> UI Streamlit: `streamlit run app.py` → `http://localhost:8501`
>
> URL public: _(cần điền sau khi chạy `cloudflared tunnel --url http://localhost:8501`)_

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | Hỏi lại người dùng khi thiếu thông tin, hoặc xin xác nhận yes/no trước hành động ghi | không |
| `timeline` | Lấy các bài đăng gần đây của một tài khoản | không |
| `social_search` | Tìm bài đăng trên mạng xã hội theo từ khóa | không |
| `lookup` | Tìm thông tin / tin tức trên web | không |
| `fetch` | Đọc nội dung từ một URL | không |
| `format` | Trình bày các item đã có thành digest markdown | không |
| `send` | Gửi một đoạn text lên Telegram | không (optional built-in) |
| `policy` | Tìm trong tài liệu policy nội bộ | không (optional built-in) |
| `papers` | Tìm bài báo khoa học trên arXiv | không (optional built-in) |
| `paper_text` | Tải PDF arXiv và trích text | không (optional built-in) |

> ⚠️ **Còn thiếu so với yêu cầu bắt buộc**: nhóm chưa tự viết tool mới nào. README yêu cầu tối thiểu 1 tool mới kèm `TOOL.md`, đăng ký trong `tools/__init__.py` và `tools.yaml`. Hiện `TOOL_FUNCTIONS` vẫn đúng 10 tool của starter.

## A3. Câu hỏi mẫu để thử

1. `Tin tức AI hôm nay có gì nổi bật?` — routing sang `lookup` với `topic=news`, `timeframe=day`.
2. `Tóm tắt 5 tweet mới nhất giúp mình` — thiếu handle → agent phải hỏi lại, không được đoán bừa.
3. `Tìm trên web tin AI hôm nay và tìm thêm tweet về AI.` — gọi song song `lookup` + `social_search`.
4. `Đăng bản tin này lên Telegram giúp mình` — phải xin xác nhận trước, không tự gửi.
5. `Tìm giúp mình vài bài báo khoa học về multimodal learning trên arXiv.` — routing sang `papers`.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| `Tóm tắt 5 tweet mới nhất giúp mình` | v0: `timeline(screenname="sama")` → v4: `clarify(response_type="text")` | v0 đoán bừa tài khoản Sam Altman; v4 hỏi lại | `runs/v0_...103628357300.json` (R10) vs `runs/v4_...112824143866.json` |
| `Tìm trên web tin AI hôm nay và tìm thêm tweet về AI.` | 2 tool song song; `query="AI"` ở cả hai | v0/v3 nhét cả cụm `"tin AI hôm nay"` vào query; v4 chỉ còn `"AI"` | R13 trong run v3 vs v4 |
| `Đăng bản tin này lên Telegram giúp mình` | v0: `send(...)` ngay → v4: `clarify(...)` | v0 gửi thẳng; v4 chặn lại hỏi trước | R12 trong run v0 vs v4 |
| `Tìm một bài báo 2026 về tế bào gốc, tóm tắt và đăng lên Telegram` | v0: `papers`→`fetch`→`send`×2; v4: chỉ `papers` rồi trả lời | v0 vượt ranh giới gửi 2 lần; v4 dừng đúng chỗ và báo không có bài 2026 | `transcripts/v0_...123825394807` vs `transcripts/v4_...123832706016` |
| Chế độ **So sánh version** trên UI | Chạy cùng 1 scenario trên v0 và v4 cạnh nhau | Toàn bộ câu chuyện trên một màn hình | `app.py` → sidebar → "So sánh version" |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ đã kiểm tra: **mọi run đều có `provider_error_cases = 0` và `measured_cases = total_cases`.**

## B1. Version evidence

Metric = `summary.case_accuracy` trên `data/eval_base.json` (20 case).

| Version | Prompt/tool change | Hypothesis | Metric | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline (artifact cố tình mơ hồ) | — | case_accuracy | — | 0.70 | `runs/v0_B_base_openrouter_20260729T103628357300.json` |
| v1 | **prompt**: hỏi lại thay vì đoán handle/URL; xin duyệt trước khi gửi; **bỏ** câu "Always finish in a single step. Pick one tool" | Đặt tên `clarify` làm phản ứng cho thiếu arg bắt buộc sẽ sửa R10/R11; bỏ ràng buộc một-tool mở khoá cả case không cần tool lẫn case song song | case_accuracy | 0.70 | **0.85** | `runs/v1_B_base_openrouter_20260729T104505362971.json` |
| v2 | **tools**: đưa `response_type` và `topic` vào `required` kèm mô tả enum | Bắt model buộc phải phát ra enum đang bị bỏ trống sẽ sửa R11/R12/R13 | case_accuracy | 0.85 | **0.80** ↓ | `runs/v2_B_base_openrouter_20260729T105854261346.json` |
| v3 | **both**: chuyển mô tả `topic` về đúng key; tăng cường mô tả routing `lookup`; thêm cổng `yes_no` và quy tắc enum tường minh vào prompt | Sửa chỗ dán nhầm sẽ lấy lại R03/M06 | case_accuracy | 0.80 | **0.90** | `runs/v3_B_base_openrouter_20260729T110742565755.json` |
| v4 | **tools**: ghim `lookup.query` bằng quy tắc không-trùng-lặp | `query` chỉ chứa chủ đề, không lặp lại thứ `topic`/`timeframe`/lựa chọn tool đã mã hoá | case_accuracy | 0.90 | **0.95** | `runs/v4_B_base_openrouter_20260729T112824143866.json` |

Chi tiết 4 metric:

| Version | case_accuracy | routing | argument | multiturn |
|---|---:|---:|---:|---:|
| v0 | 0.70 | 0.75 | 0.70 | 1.00 |
| v1 | 0.85 | 1.00 | 0.85 | 1.00 |
| v2 | 0.80 | 0.95 | 0.80 | 0.83 |
| v3 | 0.90 | 1.00 | 0.90 | 1.00 |
| v4 | **0.95** | **1.00** | **0.95** | **1.00** |

### Điều học được từ v2 (version duy nhất bị tụt)

v2 là entry có giá trị nhất trong version log. Nó **vừa đúng vừa sai cùng lúc**:

- **Đúng**: đưa enum vào `required` đã xoá hẳn lỗi `topic: None` và sửa R11.
- **Sai 1 — dán nhầm key**: đoạn mô tả dành cho `topic` bị dán vào `timeframe`, mô tả các giá trị (`news`/`general`) thậm chí không nằm trong enum của `timeframe`. Hệ quả là R03 hỏng (`query` trở thành cả cụm `"tin tức AI hôm nay"`).
- **Sai 2 — chi phí của `required`**: thêm một arg bắt buộc vào `lookup` làm tool này "đắt" hơn khi gọi, nên ở M06 model bám lấy `social_search` (chỉ cần `query`). Multiturn tụt 1.00 → 0.83.

Bài học: một arg đang PASS nhưng **chưa được đặc tả ở đâu cả** thì không phải là đã sửa, chỉ là chưa bị lật. `query="AI"` ở v1 là may mắn, và v2 đã chứng minh điều đó.

## B2. Failure analysis

### Base eval — các failure đã sửa

| Case ID | Failure Type | Actual Tool Calls (v0) | What Failed | Fix (version) |
|---|---|---|---|---|
| R08 | out_of_scope | `send(text="nguyên hàm của x²...")` | Prompt ép "Always finish... Pick one tool" nên luôn phải gọi tool | Bỏ câu đó khỏi prompt (v1) |
| R14 | out_of_scope | `send(text=<code Fibonacci>)` | Như trên | v1 |
| R10 | missing_info | `timeline(screenname="sama")` | Prompt bảo "pick a well-known account like Sam Altman" | Quy tắc: thiếu arg **bắt buộc** → `clarify` (v1) |
| R11 | missing_info | `fetch(url="https://example.com/article")` | Prompt bảo "assume a likely URL" | v1 (routing) + `response_type` vào `required` (v2) |
| R03 | wrong_arg_value | `lookup(query="tin tức AI hôm nay")` | Mô tả `topic` bị dán nhầm sang `timeframe` | Chuyển về đúng key (v3) |
| M06 | wrong_tool | `social_search(...)` thay vì `lookup` | `required` mới làm `lookup` "đắt" hơn | Tăng cường mô tả routing của `lookup` (v3) |
| R13 | wrong_arg_value | `lookup(query="tin AI hôm nay")` | `lookup.query` chỉ có mô tả `"Truy vấn"` | Quy tắc không-trùng-lặp (v4) |

### Base eval — failure còn lại ở v4

| Case ID | Failure Type | Actual | What Failed |
|---|---|---|---|
| R12 | wrong_boundary | `clarify(question="Bạn có thể cung cấp nội dung...", response_type="text")` | Kỳ vọng `response_type="yes_no"` |

**Nguyên nhân — xung đột thứ tự luật trong prompt, không phải sai chữ.** Dòng L4 ("Whenever something is missing or unclear... ask for clarification") đứng **trước** dòng L6 (cổng gửi `yes_no`). Trong R12, cụm "bản tin này" không có tiền ngữ nên nội dung **thực sự thiếu** → điều kiện của L4 khớp trước và thắng. Bằng chứng nằm ngay trong câu hỏi agent đặt ra: nó hỏi **nội dung** ("Bạn có thể cung cấp nội dung cụ thể của bản tin...") chứ không hỏi **phê duyệt**. Cách sửa là thêm ngoại lệ vào L4 và ghi đè ở L6, chứ không phải sửa `tools.yaml`.

## B3. Team eval cases

10 case tự viết trong `data/eval_group.json` (`dataset_id: day04_v4_research_group`), 5 single-turn + 5 multi-turn.

**Nguyên tắc thiết kế: không lặp lại thứ `eval_base` đã đo.** Mỗi case nhắm vào phần bề mặt mà v0–v4 **chưa từng bị chấm**: các bonus tool, các enum chưa được đặc tả (`search_type=Top`, `topic=general`, `confirmed=true`), tính tổng quát của quy tắc `query`, mặt còn lại của ranh giới gửi, và rủi ro hỏi lại thừa.

Run: `runs/v4_B_group_openrouter_20260729T113938643002.json` — **case_accuracy 0.60**, routing 0.80, argument 0.60, **multiturn 0.40**.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01 | Routing sang bonus tool | `papers(query="multimodal learning")` | ✅ PASS |
| G02 | `topic=general`, không lạm dụng `news` | `lookup(query="dân số Việt Nam", topic="general")` | ✅ PASS |
| G03 | `"quan tâm nhiều nhất"` → `Top` | `social_search(query="VinFast", search_type="Top")` | ✅ PASS |
| G04 | Quy tắc `query` tổng quát ngoài chủ đề AI | `lookup(query="bầu cử Mỹ", topic="news", timeframe="month")` | ✅ PASS |
| G05 | Không hỏi lại thừa + map tên → handle | `timeline(screenname="GoogleDeepMind")` | ❌ FAIL |
| G06 | Gửi sau khi đã được duyệt rõ ràng | `send(confirmed=true)` | ❌ FAIL |
| G07 | Sửa `timeframe` week → month qua 3 lượt | `lookup(query="công nghệ", topic="news", timeframe="month")` | ✅ PASS |
| G08 | Phân biệt `paper_text` vs `fetch` (cùng nhận URL) | `paper_text(arxiv_url="...2006.11239")` | ✅ PASS |
| G09 | `"bài đó"` mơ hồ → phải hỏi lại | `clarify(response_type="text")` | ❌ FAIL |
| G10 | Song song + đại từ `"nó"` qua 2 lượt | `lookup(topic="news")` + `social_search` | ❌ FAIL |

### Bốn vấn đề stress test phát hiện được

Đây là phần giá trị nhất: **agent đạt 0.95 trên base nhưng chỉ 0.60 trên bộ case của nhóm**, và multiturn tụt từ 1.00 xuống 0.40. Base eval đã bị "vắt" cạn qua 4 vòng tối ưu nên không còn đo được gì mới; bộ group mới cho thấy agent thực sự yếu ở đâu khi chạy live.

**1. G05 — map tên hiển thị sang handle không đáng tin.**
```
expect: screenname="GoogleDeepMind"   actual: screenname="DeepMind"
```
Agent gọi đúng tool, đúng ý định, nhưng **bịa sai handle**. Đây là lỗi nguy hiểm nhất khi chạy live: request vẫn "thành công" nhưng trả về dữ liệu của tài khoản khác hoặc 404 — không có tín hiệu nào báo sai. `timeline.screenname` hiện chỉ được mô tả là `"Tên tài khoản"`, không nói phải là handle chính xác và không nói phải làm gì khi không chắc.

**2. G06 — cổng xác nhận bị kẹt, không bao giờ mở.**
```
turn 3: "Mình đồng ý, bạn đăng đi."
actual: clarify(question="Bạn có muốn đăng bản tin này lên kênh Telegram nào cụ thể không?", response_type="yes_no")
```
Người dùng đã duyệt tường minh, agent vẫn hỏi tiếp một câu **mới**. Luật `send` ở v3 chỉ dạy agent *chặn*, chưa bao giờ dạy nó *đi tiếp*. Kết quả là `confirmed=true` không bao giờ được đặt và `send` không bao giờ chạy. Ghép với R12 (base) thì thấy rõ: **cả hai đầu của ranh giới gửi đều sai** — R12 chặn nhầm cách, G06 không chịu mở.

**3. G09 — luật hỏi lại chỉ phủ đúng hai arg.**
```
turn 2: "Đọc toàn văn bài đó cho mình."
actual: papers(query="reinforcement learning", max_results=1)
```
`"bài đó"` không xác định được, nhưng thay vì hỏi lại agent tự đặt `max_results=1` để ép ra một bài rồi coi đó là "bài đó". Prompt v1 liệt kê đích danh `screenname` và `url` là các arg bắt buộc cần hỏi lại; `arxiv_url` không nằm trong danh sách nên đường `papers`/`paper_text` hoàn toàn không được bảo vệ. Luật đang **liệt kê tên arg** thay vì nêu nguyên tắc.

**4. G10 — suy luận `topic` không vượt qua ranh giới lượt.**
```
expect: topic="news"   actual: topic="general"
```
Tín hiệu `"tin"` nằm ở lượt 2 còn chủ đề `Gemini` ở lượt 1. Khi cả hai nằm chung một câu (G04, R03) agent làm đúng; khi bị tách qua hai lượt thì hỏng. Routing vẫn đúng (gọi đủ 2 tool song song), chỉ sai một arg — nhưng đủ để fail.

### Ghi chú về độ trung thực của dự đoán

Trước khi chạy, nhóm dự đoán G02, G03, G05, G06 sẽ fail vì mô tả `"Cách sắp xếp"` và `"Cờ xác nhận"` chưa bao giờ được sửa. Thực tế **G02 và G03 lại PASS**, còn G09 và G10 (không được dự đoán) lại fail. Điều này củng cố đúng bài học của v2: suy đoán từ mô tả tool không thay thế được việc chạy thật.

## B4. Live chat evidence

| Scenario/Turn | Version | Tool Calls + Args | Transcript | Outcome |
|---|---|---|---|---|
| "Tìm một bài báo vào năm 2026 về tế bào gốc, tóm tắt nội dung và đăng phần tóm tắt lên Telegram." | v0 | `papers(query="tế bào gốc", sort_by="submittedDate")` → `fetch(url="arxiv.org/abs/2607.25933v1")` → `send(text=...)` → `send(text=...)` **(2 lần)** | `transcripts/v0_openrouter_20260729T123825394807.transcript.json` | ❌ Vượt ranh giới: tự gửi Telegram không hỏi, còn retry lần 2 sau khi lỗi config |
| Cùng câu trên | v4 | `papers(query="tế bào gốc", max_results=5, sort_by="submittedDate")` — dừng lại | `transcripts/v4_openrouter_20260729T123832706016.transcript.json` | ✅ Không tự gửi; trả lời trung thực rằng không có bài nào năm 2026 |

Đây là bằng chứng live rõ nhất cho cải thiện v0 → v4: cùng một câu, v0 thực hiện hành động ghi ra ngoài **hai lần** mà không xin phép, v4 dừng đúng chỗ và không bịa kết quả.

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| **Must-have: tool mới đầu tiên** | — | ⚠️ **Chưa làm.** Nhóm chưa viết tool mới nào; `TOOL_FUNCTIONS` vẫn đúng 10 tool của starter | Đây là deliverable bắt buộc còn thiếu |
| Optional built-in — `papers` | `runs/v4_B_group_...json` (G01), transcript tế bào gốc | Routing sang arXiv đúng, `sort_by=submittedDate` hoạt động | G09: tự đặt `max_results=1` để né việc phải hỏi lại |
| Optional built-in — `paper_text` | `runs/v4_B_group_...json` (G08) | Phân biệt được với `fetch` khi URL là arXiv | Cặp `fetch`/`paper_text` vẫn là chỗ dễ nhầm nhất |
| Optional built-in — `send` | `runs/v0/v4 base` (R12), group (G06) | Guardrail tầng tool trả `needs_confirmation` đúng | Cả hai đầu ranh giới đều lỗi (R12 + G06); Telegram credentials để unset trong mọi run |
| Optional built-in — `policy` | — | Chưa dùng trong run nào | — |

## B6. Reflection

**Fix nào thuộc về `system_prompt.md`?**
Những thứ liên quan tới *ý định và ranh giới*: hỏi lại thay vì đoán, xin duyệt trước khi gửi, và bỏ ràng buộc "một tool mỗi lượt". v1 chỉ sửa prompt và đưa 0.70 → 0.85 với routing lên thẳng 1.00. Đáng chú ý là **fix có giá trị nhất lại là một phép xoá** — bỏ câu "Always finish in a single step. Pick one tool" mới mở khoá được cả case không cần tool (R08/R14) lẫn case song song (R13).

**Fix nào thuộc về `tools.yaml`?**
Những thứ liên quan tới *hình dạng của một arg*: giá trị enum nào ứng với ngữ cảnh nào, arg nào bắt buộc phải phát ra, `query` được phép chứa gì. R13 không thể sửa bằng prompt vì đó là quy ước của một field cụ thể, và nó chỉ chịu khi được phát biểu **dựa trên chính schema** ("đừng lặp lại thứ tham số khác đã mã hoá") thay vì liệt kê cụm từ thời gian.

**Failure nào cần review thủ công thay vì chấm tự động?**
R10 ở v0 chấm FAIL vì gọi `timeline` thay vì `clarify`, nhưng `tool_results` còn cho thấy chính lời gọi đó trả về `403 Forbidden` từ RapidAPI. Grader chỉ chấm `tool_calls` + args nên lỗi 403 không ảnh hưởng điểm — sửa API key sẽ **không** đổi kết quả. Ngược lại, G05 PASS ở tầng routing nhưng handle sai (`DeepMind`) sẽ trả về dữ liệu sai khi chạy thật. Cả hai đều xác nhận cảnh báo trong README: **routing PASS không chứng minh tool đã chạy đúng.**

**Cải thiện tiếp theo?**
1. Sửa R12 bằng thứ tự luật: thêm ngoại lệ vào L4 và ghi đè ở L6 (không đụng `tools.yaml`).
2. Sửa G06 bằng cách dạy prompt *mở* cổng: sau khi người dùng duyệt tường minh thì gọi `send(confirmed=true)`, không hỏi lại.
3. Tổng quát hoá luật hỏi lại từ danh sách tên arg (`screenname`, `url`) thành nguyên tắc: **bất kỳ arg bắt buộc nào không suy ra được từ hội thoại** → `clarify`. Cái này phủ luôn G09.
4. Mô tả `timeline.screenname` phải nêu rõ cần handle chính xác và phải hỏi lại khi không chắc (G05).
5. Viết tool mới bắt buộc còn thiếu.

---

## Phụ lục — Artifact & UI

**Snapshot artifact đã xác minh.** `artifacts/versions/v0/` và `artifacts/versions/v4/` chứa bản `system_prompt.md` + `tools.yaml` của từng version. Cả hai **khớp hash với `version_log.csv`**:

| Label | artifact_version | Khớp version_log |
|---|---|---|
| v0 | `v0+pf0c107a9d7a1+t011c271ef0bb` | ✅ |
| v4 | `v4+pcf22e0901fc3+tcfe116309267` | ✅ |

v1–v3 không snapshot được thành file vì chưa từng được commit riêng; các hash của chúng vẫn nằm trong `version_log.csv` và trong từng run JSON.

**UI** — `app.py` (Streamlit), tái sử dụng `run_model_tool_loop` của `chat.py` thay vì viết agent loop thứ hai:
- *Chat*: demo multi-turn, hiện trace từng tool (round, tên, args, status, result/error), tự lưu transcript.
- *So sánh version*: chạy **cùng một scenario** trên nhiều version cạnh nhau, kèm badge xác minh hash — đúng yêu cầu "cùng một scenario demo được chạy qua nhiều prompt/tool version" của README.

```bash
cd starter_v0
.venv/bin/python -m pip install -r requirements.txt   # streamlit chưa có trong .venv
streamlit run app.py
```
