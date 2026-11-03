<h2>Open WebUI</h2>

<p>Open WebUI là <a href="https://docs.openwebui.com/"><strong>ngôi nhà dành cho AI</strong></a>: một nền tảng tự lưu trữ, dễ mở rộng, dễ sử dụng và được thiết kế để hoạt động hoàn toàn ngoại tuyến. Kết nối mô hình cục bộ qua Ollama hoặc dùng API tương thích với OpenAI cho các mô hình cục bộ và trên đám mây.</p>

[English](README.md) |
[简体中文](README.zh.md) |
[繁體中文](README.zht.md) |
[한국어](README.ko.md) |
[Deutsch](README.de.md) |
[Español](README.es.md) |
[Français](README.fr.md) |
[Italiano](README.it.md) |
[Dansk](README.da.md) |
[日本語](README.ja.md) |
[Polski](README.pl.md) |
[Русский](README.ru.md) |
[Bosanski](README.bs.md) |
[العربية](README.ar.md) |
[Norsk](README.no.md) |
[Português (Brasil)](README.br.md) |
[ไทย](README.th.md) |
[Türkçe](README.tr.md) |
[Українська](README.uk.md) |
[বাংলা](README.bn.md) |
[Ελληνικά](README.gr.md) |
[Tiếng Việt](README.vi.md)

[![Bản trình diễn Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Khám phá Open WebUI →](https://docs.openwebui.com/)

### Cài đặt

#### Python

Yêu cầu Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Sau đó mở [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Sau đó mở [http://localhost:3000](http://localhost:3000).

| Thẻ image | Nội dung                                                                             |
| --------- | ------------------------------------------------------------------------------------ |
| `:main`   | Image tiêu chuẩn với các thư viện phụ thuộc cho AI cục bộ                            |
| `:slim`   | Image gọn nhẹ dùng dịch vụ bên ngoài cho embedding, trích xuất tài liệu và giọng nói |
| `:cuda`   | Open WebUI với tăng tốc CUDA                                                         |
| `:ollama` | Open WebUI tích hợp sẵn Ollama                                                       |
| `:dev`    | Bản dựng phát triển mới nhất                                                         |

Thêm các tùy chọn sau vào `docker run` trước tên image khi cần:

| Tùy chọn                                             | Mục đích                                                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Kết nối đến Ollama trên máy chủ khác                                                       |
| `-e OPENAI_API_KEY=your_secret_key`                  | Thiết lập khóa API OpenAI                                                                  |
| `-e HF_HUB_OFFLINE=1`                                | Tắt tải mô hình Hugging Face để sử dụng ngoại tuyến                                        |
| `--gpus all`                                         | Bật quyền truy cập GPU Nvidia cho `:cuda` hoặc `:ollama`; yêu cầu Nvidia Container Toolkit |

Xem [hướng dẫn cài đặt Docker](https://docs.openwebui.com/getting-started/quick-start/) để biết các bước thiết lập và tùy chọn cấu hình.

#### Ứng dụng máy tính

[Tải ứng dụng máy tính gốc](https://github.com/open-webui/desktop) cho macOS, Windows và Linux.

[Đọc tài liệu →](https://docs.openwebui.com/getting-started/)

### Hệ sinh thái

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Lớp thực thi biến Open WebUI thành môi trường tác tử hoàn chỉnh, với khả năng điều phối cấp doanh nghiệp cho không gian làm việc riêng của từng người dùng.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Đồng bộ các thư mục, kho mã, bucket và wiki vào cơ sở tri thức Open WebUI theo kiểu gia tăng.
- [Open WebUI Computer](https://github.com/open-webui/computer): Máy tính của bạn trong bất kỳ trình duyệt nào: tệp, trình soạn thảo, terminal, Git và các tác tử AI tùy chọn đều chạy trên máy thật của bạn.

Xem [tài liệu hệ sinh thái](https://docs.openwebui.com/ecosystem/) để biết chi tiết.

### Khắc phục sự cố và cập nhật

Xem [hướng dẫn khắc phục sự cố](https://docs.openwebui.com/troubleshooting/) khi gặp vấn đề kết nối và [hướng dẫn cập nhật](https://docs.openwebui.com/getting-started/updating) để cập nhật bản cài đặt.

### Tài liệu

Xem [tài liệu](https://docs.openwebui.com/) để biết cách cấu hình và sử dụng, cùng [lộ trình](https://docs.openwebui.com/roadmap/) cho các công việc dự kiến.

Với Docker Compose, Kubernetes và các cách thiết lập khác, xem [tài liệu cài đặt](https://docs.openwebui.com/getting-started/).

### Hỗ trợ

[Tạo issue](https://github.com/open-webui/open-webui/issues) hoặc [bắt đầu thảo luận](https://github.com/open-webui/open-webui/discussions).

Tìm chúng tôi trên [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) và [Discord](https://discord.gg/5rJgQTnV4s).

### Bảo mật

Báo cáo lỗ hổng một cách riêng tư qua [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Báo cáo bảo mật chỉ được tiếp nhận qua GitHub.

### Lịch sử sao

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Biểu đồ lịch sử sao" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Giấy phép

Bao gồm mã theo Open WebUI License, yêu cầu giữ nguyên thương hiệu Open WebUI, và các đóng góp trước đây theo giấy phép gốc tương ứng. Xem [LICENSE](./LICENSE) và [LICENSE_HISTORY](./LICENSE_HISTORY) để biết điều khoản và lịch sử.

[Doanh nghiệp](https://docs.openwebui.com/enterprise) · [Tuyển dụng](https://careers.openwebui.com/) · [Tài trợ](https://github.com/sponsors/open-webui)

Được tạo bởi [Timothy Jaeryang Baek](https://github.com/tjbck).
