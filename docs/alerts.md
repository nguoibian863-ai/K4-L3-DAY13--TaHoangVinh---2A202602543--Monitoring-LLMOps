# Alert và runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## High user-visible latency

- Tên: High user-visible latency
- Severity: Critical
- Duration: 5 phút
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: P95 latency và SLO `fast_successful_requests`.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục 5 phút.
- Ảnh hưởng tới người dùng: Phản hồi chat chậm hơn ngưỡng chấp nhận, có nguy cơ timeout.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận P50/P95/P99 và TTFT trên dashboard trong cùng cửa sổ.
  2. Lọc log `response_sent` chậm, lấy `correlation_id` và feature bị ảnh hưởng.
  3. Mở trace tương ứng, so thời gian child `retrieval` với `fake-llm-generation`.
- Mitigation tạm thời: Giảm concurrency, chuyển traffic khỏi dependency chậm hoặc dùng prompt/model fallback đã kiểm chứng.
- Owner: `on-call-platform`

## Elevated request failures

- Tên: Elevated request failures
- Severity: Critical
- Duration: 5 phút
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: Error rate guardrail tối đa 2% và retrieval success tối thiểu 90%.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục 5 phút.
- Ảnh hưởng tới người dùng: Request trả lỗi hoặc không lấy được context cần thiết.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra error breakdown và retrieval success trên dashboard.
  2. Nhóm `request_failed` theo `error_type`, `feature` và `model`.
  3. Theo `correlation_id` sang trace để xác định child observation lỗi.
- Mitigation tạm thời: Tắt incident/feature lỗi, retry có giới hạn hoặc phục vụ câu trả lời fallback an toàn.
- Owner: `on-call-platform`

## Degraded answer quality

- Tên: Degraded answer quality
- Severity: Warning
- Duration: 10 phút
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: Quality proxy guardrail trung bình tối thiểu 0.75.
- Điều kiện và thời gian duy trì: `quality_score_mean < 0.75` liên tục 10 phút.
- Ảnh hưởng tới người dùng: Câu trả lời kém liên quan hoặc không đủ context dù request vẫn thành công.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận quality giảm theo feature/model và kiểm tra token/cost có thay đổi đồng thời không.
  2. So sánh prompt name, label và version trong các trace trước/sau thời điểm giảm.
  3. Kiểm tra output retrieval đã đủ tài liệu trước khi đánh giá generation.
- Mitigation tạm thời: Rollback label `production` về prompt baseline v1 và theo dõi quality trong 10 phút tiếp theo.
- Owner: `llm-quality`
