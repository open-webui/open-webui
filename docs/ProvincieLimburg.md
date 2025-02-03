# Documentatie Pilot-Implementatie Provincie Limburg
De Provincie Limburg voert een pilot uit waarin AI-taalmodellen worden geïmplementeerd binnen een veilige en schaalbare infrastructuur. Deze documentatie beschrijft deze implementatie.

## Doelstellingen:
- Verkennen van de toepassingsmogelijkheden van taalmodellen.
- Ondersteuning bieden aan projecten binnen verschillende domeinen van de Provincie.
- Waarborging van dataveiligheid en naleving van regelgeving.

## Gebruik een `.env`-bestand
Om gevoelige informatie, zoals API-sleutels en wachtwoorden, veilig te beheren, maken we gebruik van een .env-bestand. Dit bestand bevat de variabelen die door Docker en andere componenten worden opgehaald tijdens de uitvoering van de omgeving.

### Locatie:
Plaats het .env-bestand in de hoofdmappen van de respectieve configuraties, bijvoorbeeld:

- Voor docker-compose.yml: in `app`
- Voor specifieke configuraties van LiteLLM: in `app/litellm`

## Overzicht van de Componenten
| **Wat**             | **Leverancier**          | **Details**                                    |
|----------------------|--------------------------|------------------------------------------------|
| **Taalmodellen**     | Microsoft Azure          | GPT-4o, DeepSeek-R1, text-embeddings-3-large  |
| **Taalmodellen**     | Google Vertex AI         | Claude-3.5-Sonnet                              |
| **Virtual Machine**  | Hetzner via Elestio     | Hosting van infrastructuur                    |
| **Authenticatie**    | Microsoft Entra ID       | Single sign-on en beveiligde login            |

## Stap 1: .env-bestand opstellen
Maak een .env-bestand in `app/` en voeg de volgende variabelen toe. Vul onderstaande placeholders in met jouw eigen API-sleutels, URL's en gegevens.

```
# Algemene instellingen
$SOFTWARE_VERSION_TAG=<versie>
ADMIN_EMAIL=<jouw_admin_email>
ENV=<development|production>
ENABLE_SIGNUP=true
ENABLE_LOGIN_FORM=true

# Microsoft authenticatie
MICROSOFT_CLIENT_ID=<jouw_client_id>
MICROSOFT_CLIENT_SECRET=<jouw_client_secret>
MICROSOFT_CLIENT_TENANT_ID=<jouw_tenant_id>
MICROSOFT_REDIRECT_URI=<jouw_redirect_uri>
MICROSOFT_OAUTH_SCOPE="openid profile email offline_access"

# Azure-instellingen
AZURE_API_KEY=<jouw_azure_api_key>
AZURE_API_BASE=<jouw_azure_api_base_url>
AZURE_API_VERSION=<jouw_azure_api_version>

# Google Vertex AI
VERTEX_PROJECT=<jouw_vertex_project_id>
VERTEX_LOCATION=<jouw_vertex_locatie>
VERTEX_CREDENTIALS_FILE=calcium-alchemy-416511-58b3843781ae.json

# Web interface instellingen
WEBUI_SECRET_KEY=<jouw_webui_secret_key>
WEBUI_NAME=<project_naam>
WEBUI_URL=<web_url>

# Overige instellingen
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false
```

## Stap 2: docker-compose.yml configuratie
De configuratie in `app/docker-compose.yml` wordt aangepast om gebruik te maken van de waarden in het `.env`-bestand. Hieronder de verbeterde configuratie:

```
version: "3.3"
services:
  open-webui:
    image: ghcr.io/jeannotdamoiseaux/open-webui:$SOFTWARE_VERSION_TAG
    restart: always
    ports:
      - 172.17.0.1:18462:8080
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - ADMIN_EMAIL=${ADMIN_EMAIL}
      - ENV=${ENV}
      - ENABLE_SIGNUP=${ENABLE_SIGNUP}
      - SCARF_NO_ANALYTICS=true
      - DO_NOT_TRACK=${DO_NOT_TRACK}
      - ANONYMIZED_TELEMETRY=${ANONYMIZED_TELEMETRY}
      - WEBUI_NAME=${WEBUI_NAME}
      - WEBUI_URL=${WEBUI_URL}
      - OAUTH_PROVIDER_NAME=Microsoft
      - MICROSOFT_OAUTH_SCOPE=${MICROSOFT_OAUTH_SCOPE}
      - ENABLE_OAUTH_SIGNUP=${ENABLE_SIGNUP}
      - ENABLE_LOGIN_FORM=${ENABLE_LOGIN_FORM}
      - MICROSOFT_REDIRECT_URI=${MICROSOFT_REDIRECT_URI}
      - MICROSOFT_CLIENT_ID=${MICROSOFT_CLIENT_ID}
      - MICROSOFT_CLIENT_SECRET=${MICROSOFT_CLIENT_SECRET}
      - MICROSOFT_CLIENT_TENANT_ID=${MICROSOFT_CLIENT_TENANT_ID}
      - OPENAI_API_BASE_URL=http://litellm:4000
    volumes:
      - ./open-webui:/app/backend/data
    depends_on:
      - ollama
      - litellm
    extra_hosts:
      - host.docker.internal:host-gateway

  ollama:
    image: ollama/ollama:latest
    restart: always
    expose:
      - 11434:11434
    pull_policy: always
    tty: true
    volumes:
      - ./ollama:/root/.ollama

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    restart: always
    ports:
      - 4000:4000
    environment:
      - AZURE_API_KEY=${AZURE_API_KEY}
      - AZURE_API_BASE=${AZURE_API_BASE}
      - AZURE_API_VERSION=${AZURE_API_VERSION}
      - VERTEX_PROJECT=${VERTEX_PROJECT}
      - VERTEX_LOCATION=${VERTEX_LOCATION}
      - VERTEX_CREDENTIALS_FILE=${VERTEX_CREDENTIALS_FILE}
    volumes:
      - ./litellm/litellm_config.yaml:/app/config.yaml
      - ./litellm/${VERTEX_CREDENTIALS_FILE}:/app/${VERTEX_CREDENTIALS_FILE}
    command: --config /app/config.yaml --detailed_debug
```

## Stap 3: LiteLLM Configuratie
Werk de configuratie in `app/litellm/litellm_config.yaml` bij zodat alle gevoelige variabelen worden opgehaald uit de omgevingsvariabelen in het `.env`-bestand:

```
model_list:
  - model_name: azure-gpt-4o
    litellm_params:
      model: azure/gpt-4o
      api_base: ${AZURE_API_BASE}
      api_key: ${AZURE_API_KEY}
      api_version: ${AZURE_API_VERSION}

  - model_name: azure-text-embedding-3-large
    litellm_params:
      model: azure/text-embedding-3-large
      api_base: ${AZURE_API_BASE}
      api_key: ${AZURE_API_KEY}
      api_version: ${AZURE_API_VERSION}

  - model_name: azure-deepseek-r1
    litellm_params:
      model: azure_ai/DeepSeek-R1-wlvjj
      api_base: https://DeepSeek-R1-wlvjj.westus.models.ai.azure.com
      api_key: ${AZURE_API_KEY}
      api_version: ${AZURE_API_VERSION}

  - model_name: vertex-claude-3.5-sonnet
    litellm_params:
      model: vertex_ai/claude-3-5-sonnet@20240620
      vertex_project: ${VERTEX_PROJECT}
      vertex_location: ${VERTEX_LOCATION}
      vertex_credentials: ${VERTEX_CREDENTIALS_FILE}
```

## Stap 4: LiteLLM Connectie Finaliseren
Om de verbinding met LiteLLM volledig te configureren, zorg je ervoor dat de API Base URL correct is ingesteld in de beheerdersinstellingen van de webinterface.

Stappen:
1. Log in op de Webinterface:
3. Gebruik je beheerdersaccount om in te loggen.
3. Klik op Beheerdersinstellingen in het menu.
4. Ga naar het tabblad Verbindingen .
5. API Base URL Instellen:
6. Voeg de volgende waarde toe aan het veld API Base URL bij OpenAI API:
`http://litellm:4000`
Dit is de interne URL die door de Docker-containers wordt gebruikt om de LiteLLM-service te bereiken.

7. Opslaan:
Klik op Opslaan (of de equivalente knop) om de wijzigingen te bevestigen.
