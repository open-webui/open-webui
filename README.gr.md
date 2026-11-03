<h2>Open WebUI</h2>

<p>Το Open WebUI είναι <a href="https://docs.openwebui.com/"><strong>ένα σπίτι για την τεχνητή νοημοσύνη</strong></a>: μια επεκτάσιμη, εύχρηστη πλατφόρμα που φιλοξενείτε εσείς, σχεδιασμένη να λειτουργεί πλήρως εκτός σύνδεσης. Συνδέστε τοπικά μοντέλα μέσω του Ollama ή χρησιμοποιήστε API συμβατά με το OpenAI για τοπικά μοντέλα και μοντέλα στο cloud.</p>

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

[![Επίδειξη του Open WebUI](https://cdn.openwebui.com/open-webui-demo.gif)](https://docs.openwebui.com/)

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=Support&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

[Εξερευνήστε το Open WebUI →](https://docs.openwebui.com/)

### Εγκατάσταση

#### Python

Απαιτείται Python 3.12.

```bash
pip install open-webui
open-webui serve
```

Στη συνέχεια, ανοίξτε το [http://localhost:8080](http://localhost:8080).

#### Docker

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

Στη συνέχεια, ανοίξτε το [http://localhost:3000](http://localhost:3000).

| Ετικέτα εικόνας | Περιεχόμενο                                                                                                 |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| `:main`         | Τυπική εικόνα με εξαρτήσεις για τοπική AI                                                                   |
| `:slim`         | Ελαφριά εικόνα που χρησιμοποιεί εξωτερικές υπηρεσίες για embeddings, εξαγωγή περιεχομένου εγγράφων και φωνή |
| `:cuda`         | Open WebUI με επιτάχυνση CUDA                                                                               |
| `:ollama`       | Open WebUI με ενσωματωμένο Ollama                                                                           |
| `:dev`          | Νεότερη έκδοση ανάπτυξης                                                                                    |

Προσθέστε αυτές τις επιλογές στο `docker run` πριν από το όνομα της εικόνας, ανάλογα με τις ανάγκες σας:

| Επιλογή                                              | Σκοπός                                                                                            |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `-e OLLAMA_BASE_URL=http://your-ollama-server:11434` | Σύνδεση με Ollama σε άλλον διακομιστή                                                             |
| `-e OPENAI_API_KEY=your_secret_key`                  | Ορισμός του κλειδιού API OpenAI                                                                   |
| `-e HF_HUB_OFFLINE=1`                                | Απενεργοποίηση λήψεων μοντέλων Hugging Face για χρήση εκτός σύνδεσης                              |
| `--gpus all`                                         | Ενεργοποίηση πρόσβασης σε GPU Nvidia για `:cuda` ή `:ollama`· απαιτείται Nvidia Container Toolkit |

Δείτε τον [οδηγό εγκατάστασης με Docker](https://docs.openwebui.com/getting-started/quick-start/) για οδηγίες και επιλογές διαμόρφωσης.

#### Εφαρμογή υπολογιστή

[Κατεβάστε την εγγενή εφαρμογή υπολογιστή](https://github.com/open-webui/desktop) για macOS, Windows και Linux.

[Διαβάστε την τεκμηρίωση →](https://docs.openwebui.com/getting-started/)

### Οικοσύστημα

- [Open Terminal](https://github.com/open-webui/open-terminal) / [Terminals (Enterprise)](https://github.com/open-webui/terminals): Το επίπεδο εκτέλεσης που μετατρέπει το Open WebUI σε πλήρες περιβάλλον πρακτόρων, με εταιρική ενορχήστρωση χώρων εργασίας ανά χρήστη.
- [Knowledge Base Sync (oikb)](https://github.com/open-webui/oikb): Αντικατοπτρίστε φακέλους, αποθετήρια, buckets και wiki στις βάσεις γνώσεων του Open WebUI με αυξητικό συγχρονισμό.
- [Open WebUI Computer](https://github.com/open-webui/computer): Ο υπολογιστής σας σε οποιονδήποτε περιηγητή: αρχεία, επεξεργαστής, τερματικό, Git και προαιρετικοί πράκτορες AI, που εκτελούνται στο πραγματικό σας μηχάνημα.

Δείτε την [τεκμηρίωση του οικοσυστήματος](https://docs.openwebui.com/ecosystem/) για λεπτομέρειες.

### Αντιμετώπιση προβλημάτων και ενημερώσεις

Δείτε τον [οδηγό αντιμετώπισης προβλημάτων](https://docs.openwebui.com/troubleshooting/) για προβλήματα σύνδεσης και τον [οδηγό ενημέρωσης](https://docs.openwebui.com/getting-started/updating) για να ενημερώσετε την εγκατάστασή σας.

### Τεκμηρίωση

Δείτε την [τεκμηρίωση](https://docs.openwebui.com/) για τη διαμόρφωση και τη χρήση, και τον [οδικό χάρτη](https://docs.openwebui.com/roadmap/) για τις προγραμματισμένες εργασίες.

Για Docker Compose, Kubernetes και άλλες εγκαταστάσεις, δείτε την [τεκμηρίωση εγκατάστασης](https://docs.openwebui.com/getting-started/).

### Υποστήριξη

[Ανοίξτε ένα issue](https://github.com/open-webui/open-webui/issues) ή [ξεκινήστε μια συζήτηση](https://github.com/open-webui/open-webui/discussions).

Βρείτε μας στο [Reddit](https://www.reddit.com/r/OpenWebUI/), στο [X](https://x.com/OpenWebUI) και στο [Discord](https://discord.gg/5rJgQTnV4s).

### Ασφάλεια

Αναφέρετε ευπάθειες ιδιωτικά μέσω των [GitHub Security Advisories](https://github.com/open-webui/open-webui/security). Οι αναφορές ασφάλειας γίνονται δεκτές μόνο μέσω του GitHub.

### Ιστορικό αστεριών

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Γράφημα ιστορικού αστεριών" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

#### Άδεια χρήσης

Περιλαμβάνει κώδικα υπό την Open WebUI License, η οποία απαιτεί τη διατήρηση της ταυτότητας του Open WebUI, καθώς και παλαιότερες συνεισφορές υπό τις αρχικές τους άδειες. Δείτε τα [LICENSE](./LICENSE) και [LICENSE_HISTORY](./LICENSE_HISTORY) για τους όρους και το ιστορικό.

[Επιχειρήσεις](https://docs.openwebui.com/enterprise) · [Καριέρα](https://careers.openwebui.com/) · [Χορηγία](https://github.com/sponsors/open-webui)

Δημιουργήθηκε από τον [Timothy Jaeryang Baek](https://github.com/tjbck).
