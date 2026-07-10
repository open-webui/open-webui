# Higiene de arquivos duplicados — ChatND / Plataforma Nidum

> Mecanismo de manutencao que identifica arquivos com conteudo identico
> (mesmo SHA-256) espalhados pelas bases e remove copias redundantes com
> seguranca. **Dry-run por padrao**: nunca apaga sozinho.

## Principio

Nunca apagar nada sem antes ter como reconstruir. O conteudo manda, nao o
titulo. ChatND e os documentos fundadores (v29/v30) sao intocaveis.

---

## 1. Backup (antes de qualquer exclusao)

Duas camadas, porque ha dois tipos de coisa em risco: o registro (metadados)
e o conteudo (bytes).

### Camada A - Inventario (indice do que existe)
Antes de cada rodada, JSON com todos os registros de `GET /api/v1/files/`:

    backup_inventario_AAAA-MM-DD_HHMM.json

Por arquivo: id, filename, hash (SHA-256), user_id, meta (tamanho,
content-type), data e a qual base/colecao pertence. Permite saber exatamente
o que foi removido e em qual base recolocar.

### Camada B - Copia dos bytes (conteudo em si)
Para cada arquivo marcado para exclusao, baixa o conteudo
(`GET /api/v1/files/{id}/content`) ANTES do DELETE:

    backup_conteudo_AAAA-MM-DD_HHMM/
        {id}__{filename}
        manifesto.json   (id, hash, base de origem, caminho na pasta)

Restaurar = reenviar via `POST /api/v1/files/` e reacoplar a base via API.

### Onde fica
- Curto prazo: maquina local (`scratchpad/`), fora do volume do Railway.
- Recomendado: copiar o pacote para o SharePoint ou storage proprio.

> A exclusao no volume do Railway e IRREVERSIVEL e remove as 3 camadas
> (fisico + banco + vetores Chroma). Sem a Camada B, um arquivo apagado por
> engano nao volta.

### Retencao
Mantem os ultimos 5 pacotes; descarta os mais antigos.

---

## 2. Fluxo do job de higiene

    [1] LISTAR      -> GET /api/v1/files/  (todos os arquivos, todas as bases)
    [2] BACKUP-A    -> grava inventario (Camada A)
    [3] AGRUPAR     -> agrupa por hash SHA-256 (conteudo, NAO pelo titulo)
    [4] DECIDIR     -> escolhe 1 copia CANONICA por grupo (regra abaixo)
    [5] PROTEGER    -> aplica travas de seguranca; quem bate sai da lista
    [6] RELATORIO   -> mostra o que SERIA removido (dry-run) e PARA aqui
                       <- exige OK explicito para continuar
    [7] BACKUP-B    -> baixa os bytes dos que serao removidos (Camada B)
    [8] REMOVER     -> DELETE /api/v1/files/{id} (via oficial = 3 camadas)
    [9] VERIFICAR   -> GET confirma 404; loga resultado

O passo [6] e uma parede. Em modo agendado, o padrao e PARAR no relatorio e
notificar. So executa de fato com a flag `--executar`.

### Regra de escolha da copia canonica (passo 4)
Fica a copia que, em ordem de prioridade:
1. Estiver na base ativa do ChatND (a85d8a8f "MVP - Agente Chico").
2. Estiver em `Fonte/Documentos` (pasta dos fundadores).
3. Em empate, a mais antiga (preserva origem e referencias de chat).

### Travas de seguranca (passo 5) - nunca remove se:
- E a unica copia do conteudo (grupo de tamanho 1).
- E a copia canonica do grupo.
- Esta na base ativa do ChatND.
- E v29 ou v30 (Documento Fundador) - trava dura permanente.
- Esta referenciada em algum chat.
- O hash esta vazio/nulo (sem certeza de identidade -> nao toca).

### Quando rodar
- Sob demanda (recomendado no inicio).
- Agendado (ex.: semanal), sempre parando no relatorio.

### Monitoramento do volume (complementar)
Check leve que alerta quando o uso do volume passa de 80%.

---

## Uso do script

    python higiene_duplicados.py            # dry-run: lista o que seria removido
    python higiene_duplicados.py --executar # executa (backup-B + delete + verifica)

Variaveis de ambiente lidas de `.env.local`: NIDUM_API_KEY.
Constantes no topo do script: CHATND_BASE_ID, DOCS_PROTEGIDOS (v29/v30).
