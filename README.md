# GovChat-NL

Welkom bij de **GovChat-NL repository** ! 

Dit project is ontworpen voor Nederlandse **overheidsinstanties**, met als doel ondersteuning te bieden bij de implementatie van **AI-oplossingen**. Het platform faciliteert zowel **chatbots** als gespecialiseerde **AI-toepassingen**. Deze toepassingen zijn eenvoudig toegankelijk via een ingebouwde **App Launcher**. Met **GovChat-NL** kunnen organisaties een balans vinden tussen **centraal beheer** en **decentrale vrijheid**, waarbij gestandaardiseerde functionaliteiten gecombineerd worden met maatwerkopties. Het platform is volledig afgestemd op de eisen van overheidsorganisaties, onder andere op het gebied van **veiligheid**, **privacy** en **schaalbaarheid**. 

![Schermafbeelding 2025-01-31 101624](https://github.com/user-attachments/assets/6a5b689e-5804-47d0-8ce2-85a3275ea857)

## Voordelen van GovChat-NL 

- **Kant-en-klare applicatie**: Een veilig alternatief voor openbare chatbots (zoals ChatGPT, DeepSeek) of dure oplossingen (zoals Copilot) met ondersteuning voor diverse LLM's (OpenAI, Ollama, Azure AI e.a.). 
- **AI-toepassingen specifiek ontwikkeld voor de overheid**: Denk aan toepassingen op B1-taalniveau of gericht op subsidies, beschikbaar via de App Launcher 
- **Veiligheid**: Integratie met bestaande IAM-systemen (OAuth2, SSO, bv Microsoft Entra ID). 
- **Flexibele implementatie**: Aanpasbaar aan de bestaande IT-omgeving van de organisatie. 
- **Beheer**: Gebruikersrechten zijn eenvoudig te beheren via een admin paneel.

![image](https://github.com/user-attachments/assets/04da966a-05c2-4a95-ad8c-f0de95dcb60c)

## Implementatie 

GovChat-NL wordt geleverd in twee vormen: 

1. **Volledige broncode**: Geschikt voor uitgebreide en onvoorziene aanpassingen en te vinden in deze repository. 
2. **Docker Images**: Beschikbaar via de packages-sectie van deze GitHub-repository. Deze zijn ideaal voor standaardimplementaties met uitsluitend voorziene aanpassingen. 

Organisaties hebben de keuze om GovChat-NL te implementeren op lokale servers of in een cloudomgeving. Deze flexibiliteit maakt het mogelijk om GovChat-NL volledig af te stemmen op de bestaande infrastructuur. 

### Specifieke Implementatie: Provincie Limburg 

Een praktijkvoorbeeld van GovChat-NL is de implementatie bij de **Provincie Limburg**, waarbij gebruik wordt gemaakt van een Docker Image gehost in Elestio. Taalmodellen worden gehost in Microsoft Azure en Google Vertex AI. Voor meer informatie over deze specifieke uitrol kunt u [deze pagina](/docs/ProvincieLimburg.md) raadplegen. 

![Schermafbeelding 2025-01-31 102730](https://github.com/user-attachments/assets/ac30f57d-fdfa-4cf6-a1da-abb56dad1ad7)

### Andere Deploymentmogelijkheden 

GovChat-NL biedt echter vele verschillende deploymentopties. Raadpleeg hiervoor de upstream documentatie. 

## Balans tussen Centraal en Decentraal 

GovChat-NL streeft naar een optimale balans tussen centraal beheer en decentrale vrijheid: 

- **Centraal**:  
   - Kernfunctionaliteiten en belangrijke updates worden centraal onderhouden. 
   - Ontwikkeling van nieuwe AI-toepassingen vindt centraal plaats. 

- **Decentraal**:  
   - Overheidsorganisaties kunnen thema's, data en functionaliteiten zelfstandig aanpassen via het admin paneel. 
   - Implementaties kunnen worden toegespitst op de eigen infrastructuur. 
   - Grote wijzigingen kunnen worden doorgevoerd in een kopie van de broncode. Optioneel kunnen deze wijzigingen via een pull request worden voorgesteld voor opname in de centraal beheerde code. 

## Onderliggende repositories 

GovChat-NL is ontwikkeld op basis van open-source technologieën: 

### [OpenWebUI](https://github.com/open-webui/open-webui):  

OpenWebUI vormt de basis van GovChat-NL en biedt een veelzijdige, schaalbare architectuur. Belangrijke kenmerken: 
- Uitgebreide chatbot-interface en deployment-opties. 
- Robuust framework voor authenticatie en admin-beheer. 
- Ondersteuning voor verschillende taalmodellen (lokaal of in de cloud via standaarden zoals Ollama en OpenAI). 

 

### [LiteLLM](https://github.com/BerriAI/litellm): 

LiteLLM biedt flexibele en schaalbare integratie van Large Language Models (LLM's) Deze module biedt: 
- Een uniforme interface voor het koppelen van LLM-providers. 
- Flexibiliteit om te schakelen tussen verschillende AI-modellen en leveranciers, zoals OpenAI, Anthropic en andere. 

```mermaid 

flowchart TD 

    %% Hoofdcomponent 

    GovChatNL[GovChat-NL]:::main --> |fork| OpenWebUI:::repo; 

 

    %% Repositories met standaardstijl 

    OpenWebUI --> LokaleLLMs[Lokale LLMs]; 

    OpenWebUI --> OpenAI-standaard; 

    OpenWebUI --> Ollama-standaard; 

    OpenAI-standaard --> LiteLLM:::repo; 

 

    %% Klassen voor stijl 
    classDef main fill:#ffcc00,stroke:#333,stroke-width:3px,rounded-corners, font-size:16px, color:#000000; 

    classDef repo fill:#f9f,stroke:#333,stroke-width:2px,rounded-corners,color:#000000; 
 

``` 

## Documentatie 

GovChat-NL wordt geleverd met uitgebreide documentatie voor installatie, configuratie en beheer: 

- **Implementatiehandleiding**: Stapsgewijze uitleg voor het implementeren van GovChat-NL.  
- **Admin Paneel Handleiding**: Handleiding voor het beheren van gebruikers, instellingen en thema-aanpassingen 
- **Thema-aanpassingen**: Gedetailleerde uitleg over hoe organisaties hun chatbot kunnen aanpassen aan specifieke huisstijlrichtlijnen 
- **Beveiligingsrichtlijnen**: Documentatie over de veiligheidsmaatregelen en aanbevelingen voor het waarborgen van privacy 
- **Authenticatieopties**: Uitleg over authenticatiemethoden, zoals SSO (Single Sign-On) en OAuth-integratie.

![Schermafbeelding 2025-01-31 101515](https://github.com/user-attachments/assets/79baef23-a1ee-428e-83f3-95764d0e871a)

## Bijdragen 

We moedigen bijdragen aan deze repository aan. Raadpleeg CONTRIBUTING.md voor meer informatie over hoe je kunt bijdragen aan de ontwikkeling van GovChat-NL. 
