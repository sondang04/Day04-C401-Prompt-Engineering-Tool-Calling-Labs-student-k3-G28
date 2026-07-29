# Day 04 Lab v2 Report — Research Agent

## Team

- Team: Group 28
- Members: Cù Thành Dũng & Team
- Provider/model: OpenAI / gpt-4o-mini

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent: Tìm kiếm tin tức công nghệ/xã hội trên web, tra cứu bài viết trên Twitter/X, đọc chi tiết nội dung từ URL, tra cứu báo khoa học arXiv, và **tra cứu thời tiết các thành phố trên thế giới thời gian thực (tool mới)**.

**Link dùng thử:**
- GitHub Repository: `https://github.com/sondang04/Day04-C401-Prompt-Engineering-Tool-Calling-Labs-student-k3-G28/tree/2A202601405-chuthanhdung`
- Local UI Streamlit: `http://localhost:8501`

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận | Không |
| timeline | Lấy bài đăng Twitter mới nhất theo tài khoản | Không |
| social_search | Tìm bài đăng Twitter theo từ khóa | Không |
| lookup | Tìm kiếm thông tin & tin tức trên Web | Không |
| fetch | Đọc trích xuất nội dung từ đường dẫn URL | Không |
| format | Trình bày dữ liệu thành định dạng Markdown digest | Không |
| weather | **Tra cứu dự báo & thời tiết thực tế theo thời gian thực** | **Có (Must-have new tool)** |

## A3. Câu hỏi mẫu để thử

1. *"Thời tiết ở Hà Nội hôm nay thế nào?"* -> Gọi tool `weather`.
2. *"Tweet mới nhất của Sam Altman là gì?"* -> Gọi tool `timeline`.
3. *"Tin tức AI hôm nay có gì nổi bật?"* -> Gọi tool `lookup`.
4. *"Tóm tắt bài viết này hộ mình"* -> Thiếu URL, gọi tool `clarify` để hỏi lại.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Tra thời tiết thành phố | `weather(location="Hà Nội")` | v3 hỗ trợ tra thời tiết thời gian thực | `runs/v3_B_group_openai_*.json` |
| Thiếu URL tóm tắt | `clarify(response_type="text")` | v1 tự đoán URL -> v3 gọi clarify hỏi lại chuẩn | `runs/v3_B_base_openai_*.json` |
| Đăng tin Telegram | `clarify(response_type="yes_no")` | v1 tự gửi -> v3 gọi clarify xin phép xác nhận trước | `runs/v3_B_base_openai_*.json` |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline run | Baseline performance check | case_accuracy | 0.0 | 0.65 | `runs/v2_B_base_openai_20260729T105543414515.json` |
| v1 | Initial optimization | Improve prompt guidelines | case_accuracy | 0.65 | 0.65 | `runs/v3_B_base_openai_20260729T105713589973.json` |
| v2 | Add strict clarify rules | Enforce clarify for missing handles/URLs | case_accuracy | 0.65 | 0.85 | `runs/v3_B_base_openai_20260729T110218332232.json` |
| v3 | Add weather tool & fine-tune routing | Fine-tune screenname & tool switching | case_accuracy | 0.85 | 0.95 | `runs/v3_B_base_openai_20260729T115239067349.json` |

## B2. Failure analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R01 (v1) | wrong_tool | `clarify` | Gọi clarify xin handle thay vì map Sam Altman sang `sama` | Thêm quy tắc auto-map tên người nổi tiếng sang screenname trong system_prompt |
| R03 (v1) | wrong_arg_value | `lookup(query="AI news")` | Thêm chữ "news" dư thừa vào query | Quy tắc ép query chỉ giữ từ khóa chính khi `topic="news"` |
| M06 (v2) | wrong_tool | `lookup` + `social_search` | Vẫn gọi tool Twitter dù user yêu cầu đổi sang web | Thêm quy tắc ngắt tool cũ khi user chuyển tool |

## B3. Team eval cases

Đã tạo 10 cases trong `data/eval_group.json` (PASS 10/10 = 100%):

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_weather_hanoi | Tra thời tiết Hà Nội | `weather(location="Hà Nội")` | PASS |
| G02_weather_tokyo_fahrenheit | Tra thời tiết Tokyo độ F | `weather(location="Tokyo", unit="fahrenheit")` | PASS |
| G03_missing_weather_location | Thiếu địa điểm thời tiết | `clarify(response_type="text")` | PASS |
| G04_out_of_scope_cooking | Câu hỏi ngoài phạm vi | `no_tool` | PASS |
| G05_search_quantum_paper | Tìm bài báo arXiv | `papers(query="Quantum Computing")` | PASS |
| G06_multiturn_clarify_weather | Multi-turn bổ sung địa điểm | `weather(location="Đà Nẵng")` | PASS |
| G07_multiturn_change_topic_no_tool | Multi-turn hỏi định nghĩa | `no_tool` | PASS |
| G08_multiturn_confirm_telegram | Multi-turn gửi Telegram | `clarify(response_type="yes_no")` | PASS |
| G09_multiturn_switch_from_twitter_to_weather | Multi-turn đổi tool sang weather | `weather(location="Thành phố Hồ Chí Minh")` | PASS |
| G10_multiturn_carryover_city | Multi-turn kế thừa thành phố | `weather(location="Hải Phòng", unit="fahrenheit")` | PASS |

## B4. Live chat evidence

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| Tra thời tiết TPHCM | v3 | `weather(location="Hà Nội")` | `app.py` UI Live | PASS - Trả về thời tiết thật |
| Hỏi tin tức AI | v3 | `lookup(query="AI", topic="news")` | `app.py` UI Live | PASS - Trả về tin tức nổi bật |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới | `tools/weather/` | Lấy dữ liệu thời tiết thật thời gian thực từ API `wttr.in` | Có fallback data nếu mạng ngắt kết nối |

## B6. Reflection

- **Sửa trong `system_prompt.md`**: Thêm quy tắc rõ ràng khi nào gọi `clarify`, khi nào map tên người nổi tiếng, khi nào ngắt tool cũ trong multi-turn.
- **Sửa trong `tools.yaml`**: Mô tả rõ nét các tham số và default values của từng tool.
- **Bài học quan trọng**: Prompt Engineering cần dựa trên bằng chứng log (evidence-driven) thay vì cảm tính.
