<h2>Open WebUI</h2>

<p>Open WebUI হলো <a href="https://docs.openwebui.com/"><strong>AI-এর একটি আপন ঠিকানা</strong></a>: একটি সম্প্রসারণযোগ্য, সহজে ব্যবহারযোগ্য ও নিজে হোস্ট করা যায় এমন প্ল্যাটফর্ম, যা সম্পূর্ণ অফলাইনে চলার জন্য তৈরি। Ollama দিয়ে স্থানীয় মডেল সংযুক্ত করুন, অথবা স্থানীয় ও ক্লাউড মডেলের জন্য OpenAI-সামঞ্জস্যপূর্ণ API ব্যবহার করুন।</p>

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

[![Open WebUI ডেমো](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Open WebUI ঘুরে দেখুন →](https://docs.openwebui.com/)

### ইনস্টলেশন

#### Python

Python 3.12 প্রয়োজন।

```bash
pip install open-webui
open-webui serve
```

এরপর [http://localhost:8080](http://localhost:8080) খুলুন।

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

এরপর [http://localhost:3000](http://localhost:3000) খুলুন।

| ইমেজ ট্যাগ | যা অন্তর্ভুক্ত আছে                                                                   |
| ---------- | ------------------------------------------------------------------------------------ |
| `:main`    | স্থানীয় AI-এর প্রয়োজনীয় ডিপেন্ডেন্সিসহ স্ট্যান্ডার্ড ইমেজ                         |
| `:slim`    | এম্বেডিং, ডকুমেন্ট থেকে তথ্য আহরণ ও ভয়েসের জন্য বাহ্যিক সেবা ব্যবহার করা হালকা ইমেজ |
| `:cuda`    | CUDA অ্যাক্সেলারেশনসহ Open WebUI                                                     |
| `:ollama`  | Ollama-সহ Open WebUI                                                                 |
| `:dev`     | সর্বশেষ ডেভেলপমেন্ট বিল্ড                                                            |

প্রয়োজন অনুযায়ী `docker run` কমান্ডে ইমেজের নামের আগে এই অপশনগুলো যোগ করুন:

| অপশন                                                 | উদ্দেশ্য                                                                                           |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | অন্য সার্ভারে থাকা Ollama-তে সংযোগ করা                                                             |
| `-e OPENAI_API_KEY=your_secret_key`                  | আপনার OpenAI API কী সেট করা                                                                        |
| `-e HF_HUB_OFFLINE=1`                                | অফলাইনে ব্যবহারের জন্য Hugging Face মডেল ডাউনলোড বন্ধ করা                                          |
| `--gpus all`                                         | `:cuda` বা `:ollama`-এর জন্য Nvidia GPU ব্যবহারের অনুমতি দেওয়া; Nvidia Container Toolkit প্রয়োজন |

সেটআপের নির্দেশনা ও কনফিগারেশন অপশনের জন্য [Docker ইনস্টলেশন নির্দেশিকা](https://docs.openwebui.com/getting-started/quick-start/) দেখুন।

#### ডেস্কটপ অ্যাপ

macOS, Windows ও Linux-এর জন্য [নেটিভ ডেস্কটপ অ্যাপ ডাউনলোড করুন](https://github.com/open-webui/desktop)।

[ডকুমেন্টেশন পড়ুন →](https://docs.openwebui.com/getting-started/)

### ইকোসিস্টেম

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Open WebUI-কে একটি পূর্ণাঙ্গ এজেন্ট পরিবেশে পরিণত করার এক্সিকিউশন স্তর, যেখানে প্রত্যেক ব্যবহারকারীর ওয়ার্কস্পেসের জন্য এন্টারপ্রাইজ অর্কেস্ট্রেশন রয়েছে।
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): ইনক্রিমেন্টাল সিঙ্কের মাধ্যমে ফোল্ডার, রিপোজিটরি, বাকেট ও উইকির প্রতিলিপি Open WebUI-এর নলেজ বেসে রাখুন।
- [Open WebUI Computer](https://github.com/open-webui/computer): যেকোনো ব্রাউজারে আপনার কম্পিউটার: ফাইল, এডিটর, টার্মিনাল, Git ও ঐচ্ছিক AI এজেন্ট—সবই আপনার আসল মেশিনে চলে।

বিস্তারিত জানতে [ইকোসিস্টেম ডকুমেন্টেশন](https://docs.openwebui.com/ecosystem/) দেখুন।

### সমস্যা সমাধান ও আপডেট

সংযোগের সমস্যার জন্য [সমস্যা সমাধানের নির্দেশিকা](https://docs.openwebui.com/troubleshooting/) এবং আপনার ইনস্টলেশন আপডেট করতে [আপডেট নির্দেশিকা](https://docs.openwebui.com/getting-started/updating) দেখুন।

### ডকুমেন্টেশন

কনফিগারেশন ও ব্যবহারের জন্য [ডকুমেন্টেশন](https://docs.openwebui.com/) এবং পরিকল্পিত কাজের জন্য [রোডম্যাপ](https://docs.openwebui.com/roadmap/) দেখুন।

Docker Compose, Kubernetes ও অন্যান্য সেটআপের জন্য [ইনস্টলেশন ডকুমেন্টেশন](https://docs.openwebui.com/getting-started/) দেখুন।

### সহায়তা

[একটি ইস্যু খুলুন](https://github.com/open-webui/open-webui/issues) বা [আলোচনা শুরু করুন](https://github.com/open-webui/open-webui/discussions)।

আমাদের পাবেন [Reddit](https://www.reddit.com/r/OpenWebUI/), [X](https://x.com/OpenWebUI) ও [Discord](https://discord.gg/5rJgQTnV4s)-এ।

### নিরাপত্তা

[GitHub Security Advisories](https://github.com/open-webui/open-webui/security)-এর মাধ্যমে গোপনে নিরাপত্তা দুর্বলতা জানান। নিরাপত্তাসংক্রান্ত রিপোর্ট কেবল GitHub-এর মাধ্যমেই গ্রহণ করা হয়।

### স্টারের ইতিহাস

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="স্টারের ইতিহাসের চার্ট" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### লাইসেন্স

এতে Open WebUI License-এর আওতাধীন কোড রয়েছে, যা Open WebUI ব্র্যান্ডিং অক্ষুণ্ণ রাখা বাধ্যতামূলক করে, এবং আগের অবদানগুলো তাদের নিজ নিজ মূল লাইসেন্সের আওতায় রয়েছে। শর্ত ও ইতিহাসের জন্য [LICENSE](./LICENSE) ও [LICENSE_HISTORY](./LICENSE_HISTORY) দেখুন।

[এন্টারপ্রাইজ](https://docs.openwebui.com/enterprise) · [ক্যারিয়ার](https://careers.openwebui.com/) · [স্পনসর করুন](https://github.com/sponsors/open-webui)

তৈরি করেছেন [Timothy Jaeryang Baek](https://github.com/tjbck)।
