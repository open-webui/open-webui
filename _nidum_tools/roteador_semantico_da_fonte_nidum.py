"""
title: Roteador Semântico — Fonte e Convergências (Nidum)
author: Nidum
version: 0.2.0
description: Filtro que roteia QUALQUER frase para uma intenção canônica e injeta a resposta determinística do engine.
"""

import json, re, math, requests
from pydantic import BaseModel, Field

FONTE_INDEX = json.loads(r"""{
 "fonte": "Documento Fundador v30 + Documento Fundador v29",
 "atualizado_em": "2026-06-27",
 "orgaos": {
  "Conselho Curador": {
   "facilitador": "Sérgio Ribas",
   "membros": [
    "Andrea Fortes",
    "Assunta Camilo",
    "Flávio Littério",
    "Guilherme Brammer",
    "Ivo Pires",
    "Rodrigo Toledo",
    "Sérgio Ribas",
    "Sig Bergamin",
    "Thiago Marafon",
    "Vinicius Lummertz"
   ]
  },
  "Comitê Técnico": {
   "facilitador": "Marcelo Mendonça",
   "membros": [
    "Beatriz Bosschart",
    "Cristina Myrrha",
    "Diogo Figueiredo",
    "Felipe Saurin",
    "Lucas Takaoka",
    "Marcelo Mendonça",
    "Murilo Lomas",
    "Rachel Berrutti",
    "Riccardo Soffner",
    "Valentina Guglielmi"
   ]
  },
  "Comitê Executivo": {
   "facilitador_permanente": "Emerson Silva",
   "membros": [
    "Bruna Exposito",
    "Gabriela Sfredo",
    "Rodrigo Vaz Coelho",
    "Emerson Silva",
    "Daniel Bisol"
   ]
  }
 },
 "dedicacao_intensiva": [
  "Adriano Santos",
  "Alex Moreira Lima",
  "Amanda Bueno",
  "Amélia Reiss",
  "Bruna Exposito",
  "Carlos Magno dos Anjos",
  "Daniel Bisol",
  "Davi Agonilha Vittori",
  "Davi Vittori",
  "Edineia Jacinto",
  "Emerson Silva",
  "Fernando Neves",
  "Filipe Meneghetti",
  "Gabriela Sfredo",
  "Guilherme Clemens",
  "Iure Braga",
  "João Pedro Nóbrega",
  "Karin Adeodato",
  "Maikon Lomas",
  "Marylena Bukowski",
  "Pamela Stein",
  "Paulo Grise",
  "Pedro Shima",
  "Rachel Berrutti",
  "Raul Bueno",
  "Renato Yamashiro Kenji",
  "Riccardo Soffner",
  "Rodrigo Vaz Coelho",
  "Silvana Hoffmann",
  "Sérgio Ribas",
  "Thiago Trindade"
 ],
 "notas": {
  "Conselho Curador": "o documento cita 11; 10 constam nominalmente",
  "Comitê Técnico": "o documento cita 11; 10 constam nominalmente"
 },
 "ecossistemas_funcionais": [
  {
   "nome": "Marketing e Posicionamento",
   "facilita": "Bruna Exposito",
   "protagonistas": [
    "Alex Moreira Lima",
    "Amanda Bueno",
    "Fernando Bond",
    "Maria Vitória Vieira Viegas",
    "Marlon Rosseti",
    "Vitor Vaz Coelho"
   ]
  },
  {
   "nome": "Segmentos e Produtos",
   "facilita": "Gabriela Sfredo",
   "protagonistas": [
    "Miguel Marra",
    "Pamela Stein",
    "Rachel Berrutti",
    "Riccardo Soffner"
   ]
  },
  {
   "nome": "Operações",
   "facilita": "Rodrigo Vaz Coelho",
   "protagonistas": [
    "Amélia Reiss",
    "Bruno Divardin",
    "Carlos Magno dos Anjos",
    "Davi Agonilha Vittori",
    "Edineia Jacinto",
    "Felipe Ribeiro",
    "Fernando Neves",
    "Filipe Meneghetti",
    "Guilherme Clemens",
    "Karin Adeodato",
    "Marylena Bukowski",
    "Pedro Shima",
    "Raul Bueno",
    "Renato Yamashiro Kenji",
    "Sheedy Jaouiche"
   ]
  },
  {
   "nome": "Finanças e Gestão de Projetos",
   "facilita": "Emerson Silva",
   "protagonistas": [
    "Davi Agonilha Vittori",
    "Edineia Jacinto",
    "Fábio Trindade",
    "Iure Braga",
    "Maikon Lomas",
    "Rodrigo Toledo",
    "Thiago Trindade"
   ]
  },
  {
   "nome": "Jurídico e Governança",
   "facilita": "Daniel Bisol",
   "protagonistas": [
    "Fábio Trindade",
    "Edineia Jacinto",
    "Iure Braga",
    "Silvana Hoffmann"
   ]
  }
 ],
 "ecossistemas_produto": [
  {
   "nome": "Nidum Mundo",
   "facilita": "Riccardo Soffner",
   "protagonistas": [
    "Adriano Santos",
    "Amélia Reiss",
    "Gabriela Sfredo",
    "Miguel Marra",
    "Pamela Stein",
    "Pedro Shima",
    "Rachel Berrutti",
    "Thiago Trindade"
   ]
  },
  {
   "nome": "Nidum Brasil",
   "facilita": "Riccardo Soffner",
   "protagonistas": [
    "Adriano Santos",
    "Gabriela Sfredo",
    "Miguel Marra",
    "Pamela Stein",
    "Pedro Shima",
    "Rachel Berrutti",
    "Thiago Trindade"
   ]
  },
  {
   "nome": "Nidum Fazendas Vivas",
   "facilita": "Rachel Berrutti",
   "protagonistas": [
    "Adriano Santos",
    "Cristina Myrra",
    "Davi Vittori",
    "Gabriela Sfredo",
    "Maikon Lomas",
    "Miguel Marra",
    "Pamela Stein",
    "Pedro Shima",
    "Riccardo Soffner"
   ]
  },
  {
   "nome": "Nidum Comunidades Vivas",
   "facilita": "Rachel Berrutti",
   "protagonistas": [
    "Adriano Santos",
    "Cristina Myrra",
    "Davi Vittori",
    "Gabriela Sfredo",
    "Maikon Lomas",
    "Miguel Marra",
    "Pamela Stein",
    "Pedro Shima",
    "Riccardo Soffner"
   ]
  }
 ],
 "ecossistemas_estruturais": [
  {
   "nome": "Academia Nidum",
   "facilita": "Paulo Grise",
   "protagonistas": [
    "Adriano Santos",
    "Silvana Hoffmann",
    "Silvânia Moll"
   ]
  },
  {
   "nome": "Plataforma Tecnológica",
   "facilita": "Thiago Soares",
   "protagonistas": [
    "Alex Moreira Lima",
    "Davi Agonilha Vittori",
    "Eduardo Gentil",
    "Renato Yamashiro Kenji",
    "Thiago Trindade"
   ]
  },
  {
   "nome": "Sustentabilidade",
   "facilita": "Pedro Shima (PR Sul e SC)",
   "protagonistas": [
    "Amélia Reiss (Europa)",
    "Bruno Divardin (EUA)",
    "Fernando Neves",
    "Filipe Meneghetti",
    "Guilherme Brammer",
    "Guilherme Clemens (RS)",
    "João Pedro Nóbrega (SP)",
    "Raul Bueno (PR Norte)"
   ]
  }
 ],
 "caminho_da_obra": [
  "Originação",
  "Leitura",
  "Primeira imagem",
  "Arquiteto",
  "Gêmeo digital",
  "Batismo",
  "Ecossistema do ativo",
  "Venda por valor percebido",
  "Coautoria com o comprador",
  "Construção e formação",
  "Humanização",
  "Entrega e acolhimento",
  "Acompanhamento"
 ],
 "valores": [
  "Beleza",
  "Bondade",
  "Justiça",
  "Verdade"
 ],
 "principios_economicos": [
  "1. A Nidum não é banco. Não cobra juros sob nenhuma circunstância. Nas Comunidades Vivas, lote pago em 240 parcelas mensais, sem juros, corrigidas apenas pelo IPCA.",
  "2. Caixa é robustez, não acumulação. O caixa Nidum tem piso e teto. O piso garante operação íntegra em qualquer instante.",
  "3. Não represa dinheiro. Tudo que excede o teto ao fim do exercício vira dividendo extraordinário em paridade 50/50 entre Capital e Coautoria. Acumular além do necessário seria captura disfarçada, o oposto da tese.",
  "4. Sem comprar imóveis. A Nidum não compra imóveis. Comprar imóvel seria represar capital fora dos ecossistemas.",
  "5. Sem banco, sem intermediário. Apenas recursos próprios e contribuições dos ecossistemas. Sem financiamento bancário."
 ],
 "regua": "Em real, sem corretor, sem captura, a partir do valor mínimo de 120% da contribuição.",
 "secoes": [
  {
   "parte": "Parte I — O padrão da vida",
   "lead": "Parte I — O padrão da vida Integridade e confiança Antes de qualquer forma, há integridade. Não como meta a alcançar, mas como a condição original da qual tudo emerge. Para nomeá-la e ao seu desdobramento usamos três palavras tomadas da matemática e da experiência: Fonte é Zero, Forma é Um, Fluxo é Infinito. O Zero não é o nada, é a fonte intacta, o silêncio pleno, a potência ainda não diferenciad"
  },
  {
   "parte": "Parte II — A vitalidade",
   "lead": "Parte II — A vitalidade A inteligência num corpo vivo Antes de falar em inteligência híbrida, é preciso dizer o que é a inteligência num corpo vivo, porque ela não é o que a intuição supõe. Num organismo, a inteligência não mora em nenhuma parte. Não há, no cérebro, um ponto que comande, há redes que integram sinais em paralelo e a consciência emerge dessa integração. A inteligência do corpo é dis"
  },
  {
   "parte": "Parte III — O organismo",
   "lead": "Parte III — O organismo Nidum Resta o teste mais exigente: examinar cada ecossistema da Nidum como um órgão, dizendo a sua função, o que o potencializa quando saudável e as patologias que o ameaçam. Onde a correspondência for forçada, deve ser descartada. Aqui ela se sustentou."
  },
  {
   "parte": "Parte IV — Quem sustenta o organismo",
   "lead": "Parte IV — Quem sustenta o organismo Quem sustenta cada sistema A Nidum opera por convergência, não por hierarquia. Não há cargos no sentido clássico. Há funções que circulam. Cada órgão colegiado e cada ecossistema permanente tem um facilitador, coautor que carrega a função de buscar convergência entre vozes equivalentes. Facilitador não decide pelos demais; abre caminho para que a convergência a"
  },
  {
   "parte": "Parte V — O caminho e a engenharia",
   "lead": "Parte V — O caminho e a engenharia O caminho de uma obra Toda obra Nidum percorre a mesma espiral, da intenção à vida que a habita e sobe a cada volta. Os quatro ecossistemas de produto compartilham um só caminho de treze etapas, da originação do desejo ao acompanhamento do morador. O Comitê Técnico desenha o caminho e batiza, ao final, o projeto que se reconhece como Nidum. Concluída uma obra, a "
  },
  {
   "parte": "Parte VI — As",
   "lead": "Parte VI — As Expressões da Nidum A Nidum opera em quatro ecossistemas de produto, atravessados pela Academia, pela Sustentabilidade e pela Plataforma Tecnológica. As Unidades Produtivas, fábricas internas que verticalizam a produção, sustentam Fazenda-âncora e Comunidades Vivas e aparecem em capítulo próprio adiante. A engenharia se repete em todos os quatro. Coloca-se um ativo na plataforma. Abr"
  },
  {
   "parte": "Parte VII — As patologias e os riscos",
   "lead": "Parte VII — As patologias e os riscos Se a vitalidade é a integridade em ato, a doença é o nome que damos aos seus desalinhamentos e examiná-los de perto é a parte mais útil desta investigação, porque é diante da doença que se aprende o que era a saúde. Convém uma advertência antes de começar. O que segue não acusa pessoas, associa padrões. Nenhuma das patologias que vamos descrever é culpa de alg"
  }
 ]
}""")

CONV_INDEX = json.loads(r"""{
 "Academia Nidum": [
  {
   "prefixo": "ACA",
   "ecossistema": "Academia Nidum",
   "data_iso": "2026-06-10",
   "data_br": "10/6/2026",
   "arquivo": "ACA_Convergencia_10062026_v1.pdf",
   "movimentos": [
    "A Academia é a memória e a aprendizagem do organismo.",
    "Formar é fazer do trabalhador um coautor — e o ofício permanece na rede.",
    "A convergência é o antivírus do organismo.",
    "A confiança se cultiva — e a Academia sustenta as suas condições."
   ],
   "em_aberto": {
    "texto": "A Academia como negócio. Se e como a Academia se torna uma unidade autossustentável — formando também para o mercado, sem perder o foco no que a Nidum precisa por dentro. Em aberto. O onboarding da cultura na cadeia. Como levar a cultura e os métodos a fornecedores, parceiros e clientes, e o questionário de aproximação, que ainda depende do jurídico e dos direitos autorais. Em aberto. A formação em inteligência híbrida. Que centros e métodos adotar além do programa atual — e como tratar os aspectos humanos, como autoria e direitos, que a perspectiva técnica não cobre. Em aberto. A integração com os demais ecossistemas. Como a Academia se articula com o Comitê Técnico e com cada produto, registrando o método sem duplicar funções. Em aberto.",
    "itens": [
     {
      "tema": "A Academia como negócio",
      "texto": "A Academia como negócio. Se e como a Academia se torna uma unidade autossustentável — formando também para o mercado, sem perder o foco no que a Nidum precisa por dentro. Em aberto."
     },
     {
      "tema": "O onboarding da cultura na cadeia",
      "texto": "O onboarding da cultura na cadeia. Como levar a cultura e os métodos a fornecedores, parceiros e clientes, e o questionário de aproximação, que ainda depende do jurídico e dos direitos autorais. Em aberto."
     },
     {
      "tema": "A formação em inteligência híbrida",
      "texto": "A formação em inteligência híbrida. Que centros e métodos adotar além do programa atual — e como tratar os aspectos humanos, como autoria e direitos, que a perspectiva técnica não cobre. Em aberto."
     },
     {
      "tema": "A integração com os demais ecossistemas",
      "texto": "A integração com os demais ecossistemas. Como a Academia se articula com o Comitê Técnico e com cada produto, registrando o método sem duplicar funções. Em aberto."
     }
    ]
   },
   "proximo_passo": "Integrar a Academia aos demais ecossistemas — alinhando a formação aos processos de cada projeto e ao registro do método —, consolidar a curadoria viva do conhecimento e amadurecer o onboarding da cultura na cadeia, para que a Academia seja reconhecida como a memória e o aprendizado que mantêm a Nidum viva."
  }
 ],
 "Nidum Brasil": [
  {
   "prefixo": "BRA",
   "ecossistema": "Nidum Brasil",
   "data_iso": "2026-05-20",
   "data_br": "20/5/2026",
   "arquivo": "BRA_Convergencia_20052026_v1.pdf",
   "movimentos": [
    "A Nidum não é uma empresa de reforma. É uma plataforma de regeneração.",
    "O ninho antes da etiqueta. Não existe Nidum Brasil e Nidum Mundo — existe",
    "A coautoria como gênese — da escuta ao reconhecimento."
   ],
   "em_aberto": {
    "texto": "Quais são os tipos de cliente do Nidum Brasil? A reunião abriu três figuras: o proprietário do ativo que entra na plataforma, o comprador que adquire o ninho, e quem permanece na casa e quer regenerá-la sem vender. Cada um pede proposta de valor própria e modelo de receita próprio. O terceiro caso não está formalizado como produto na Fonte. Em aberto. O que é o gêmeo digital — e quanto custa produzi-lo? A reunião debateu dois extremos: curadoria artesanal assinada por arquiteto, lenta e cara, versus modelagem rápida por IA, genérica e sem alma. O meio-termo foi proposto mas não definido. Quantas versões por imóvel? Para quantas personas? Qual o piso de produção que mantém o método e cabe no plano? Em aberto. Como o morador encontra o ninho? O fluxo óbvio — entrar no site e comprar — não funciona. A reunião trouxe a lógica inversa: o morador é impactado antes de estar procurando. Vê o projeto, se reconhece, quer. Qual é esse canal? Como a Nidum se comunica sem cair nas ferramentas de uma sociedade egoica, que valoriza comparação em vez de verdade? Em aberto. O que acontece se o leilão não encontrar morador? A Fonte fala em venda por valor percebido. Mas não fecha o que acontece quando o leilão não encontra quem se reconheça no ninho. Segundo leilão? Refina o projeto? Sai da plataforma? Sem protocolo definido, o risco fica difuso. Em aberto.",
    "itens": [
     {
      "tema": "Quais são os tipos de cliente do Nidum Brasil? A reunião abriu três figuras: o proprietário do ativo que entra na plataforma, o comprador que adquire o ninho, e quem permanece na casa e quer regenerá-la sem vender",
      "texto": "Quais são os tipos de cliente do Nidum Brasil? A reunião abriu três figuras: o proprietário do ativo que entra na plataforma, o comprador que adquire o ninho, e quem permanece na casa e quer regenerá-la sem vender. Cada um pede proposta de valor própria e modelo de receita próprio. O terceiro caso não está formalizado como produto na Fonte. Em aberto."
     },
     {
      "tema": "O que é o gêmeo digital — e quanto custa produzi-lo? A reunião debateu dois extremos: curadoria artesanal assinada por arquiteto, lenta e cara, versus modelagem rápida por IA, genérica e sem alma",
      "texto": "O que é o gêmeo digital — e quanto custa produzi-lo? A reunião debateu dois extremos: curadoria artesanal assinada por arquiteto, lenta e cara, versus modelagem rápida por IA, genérica e sem alma. O meio-termo foi proposto mas não definido. Quantas versões por imóvel? Para quantas personas? Qual o piso de produção que mantém o método e cabe no plano? Em aberto."
     },
     {
      "tema": "Como o morador encontra o ninho? O fluxo óbvio — entrar no site e comprar — não funciona",
      "texto": "Como o morador encontra o ninho? O fluxo óbvio — entrar no site e comprar — não funciona. A reunião trouxe a lógica inversa: o morador é impactado antes de estar procurando. Vê o projeto, se reconhece, quer. Qual é esse canal? Como a Nidum se comunica sem cair nas ferramentas de uma sociedade egoica, que valoriza comparação em vez de verdade? Em aberto."
     },
     {
      "tema": "O que acontece se o leilão não encontrar morador? A Fonte fala em venda por valor percebido",
      "texto": "O que acontece se o leilão não encontrar morador? A Fonte fala em venda por valor percebido. Mas não fecha o que acontece quando o leilão não encontra quem se reconheça no ninho. Segundo leilão? Refina o projeto? Sai da plataforma? Sem protocolo definido, o risco fica difuso. Em aberto."
     }
    ]
   },
   "proximo_passo": "Quem ainda não enviou sua leitura do Nidum Brasil envia ao longo dos próximos dias — em texto, áudio, desenho, como vier. A próxima conversa continua de onde esta parou, com foco nas quatro questões em aberto acima."
  },
  {
   "prefixo": "BRA",
   "ecossistema": "Nidum Brasil",
   "data_iso": "2026-05-28",
   "data_br": "28/5/2026",
   "arquivo": "BRA_Convergencia_28052026_v1.pdf",
   "movimentos": [
    "A Nidum regenera ativos. Não pessoas, não territórios — ativos.",
    "Nidum Brasil e Nidum Mundo tendem a produto único com camadas de",
    "Ninguém coloca dinheiro antes da venda. O projeto é antes da obra — a venda",
    "As primeiras instâncias começam pelos ativos dos próprios coautores — e o"
   ],
   "em_aberto": {
    "texto": "Como o arquiteto entra no gêmeo digital — autoria, linguagem e remuneração. A reunião explorou o caminho do arquiteto-agente: cada arquiteto treina um modelo com sua linguagem e forma de projetar, e esse agente produz as versões do gêmeo. O modelo foi reconhecido como respeito à autoria humana. Mas a questão dos direitos sobre os projetos que alimentam esses agentes não foi resolvida, tampouco o modelo de remuneração nas diferentes etapas. Em aberto. Qual dos três perfis de cliente é a prioridade de entrada. A reunião identificou três figuras: o proprietário que quer vender e busca agregar valor; o comprador que adquire o ninho; e quem não quer vender, mas quer descobrir o ninho que já tem. Os três pedem proposta de valor distinta. A priorização entre eles não aconteceu. Em aberto. O custo mínimo do gêmeo digital que ainda mantém alma. A reunião entendeu que o gêmeo precisa começar barato para validar a tese. Mas não definiu o piso de qualidade abaixo do qual o gêmeo deixa de evocar o ninho e passa a ser uma renderização comum — útil tecnicamente, mas incapaz de criar o reconhecimento que justifica a venda. Em aberto. O protocolo quando a venda não se completa. O que acontece com o ninho que teve gêmeo construído, projeto desenvolvido, e não encontrou comprador em tempo razoável? Segurar o ativo, refazer o gêmeo, rever se pertence à plataforma? Sem protocolo, o risco fica difuso e o aprendizado se perde. Em aberto.",
    "itens": [
     {
      "tema": "Como o arquiteto entra no gêmeo digital — autoria, linguagem e remuneração",
      "texto": "Como o arquiteto entra no gêmeo digital — autoria, linguagem e remuneração. A reunião explorou o caminho do arquiteto-agente: cada arquiteto treina um modelo com sua linguagem e forma de projetar, e esse agente produz as versões do gêmeo. O modelo foi reconhecido como respeito à autoria humana. Mas a questão dos direitos sobre os projetos que alimentam esses agentes não foi resolvida, tampouco o modelo de remuneração nas diferentes etapas. Em aberto."
     },
     {
      "tema": "Qual dos três perfis de cliente é a prioridade de entrada",
      "texto": "Qual dos três perfis de cliente é a prioridade de entrada. A reunião identificou três figuras: o proprietário que quer vender e busca agregar valor; o comprador que adquire o ninho; e quem não quer vender, mas quer descobrir o ninho que já tem. Os três pedem proposta de valor distinta. A priorização entre eles não aconteceu. Em aberto."
     },
     {
      "tema": "O custo mínimo do gêmeo digital que ainda mantém alma",
      "texto": "O custo mínimo do gêmeo digital que ainda mantém alma. A reunião entendeu que o gêmeo precisa começar barato para validar a tese. Mas não definiu o piso de qualidade abaixo do qual o gêmeo deixa de evocar o ninho e passa a ser uma renderização comum — útil tecnicamente, mas incapaz de criar o reconhecimento que justifica a venda. Em aberto."
     },
     {
      "tema": "O protocolo quando a venda não se completa",
      "texto": "O protocolo quando a venda não se completa. O que acontece com o ninho que teve gêmeo construído, projeto desenvolvido, e não encontrou comprador em tempo razoável? Segurar o ativo, refazer o gêmeo, rever se pertence à plataforma? Sem protocolo, o risco fica difuso e o aprendizado se perde. Em aberto."
     }
    ]
   },
   "proximo_passo": "Identificar o primeiro ativo dos coautores que reúne as condições para iniciar o ciclo completo — levantamento, projeto, gêmeo, venda — e começar, sem publicar nada externamente, para que o processo seja aprendido em condições reais antes de qualquer comunicação."
  },
  {
   "prefixo": "BRA",
   "ecossistema": "Nidum Brasil",
   "data_iso": "2026-06-16",
   "data_br": "16/6/2026",
   "arquivo": "BRA_Convergencia_16062026_v1.pdf",
   "movimentos": [
    "Nidum Brasil é a pele do organismo — e o ativo que renasce de maior giro.",
    "Quem chega encontra cuidado — não um imóvel vazio.",
    "Uma célula que se divide — formando enquanto cresce.",
    "O método nasce no fluxo — e a autoria permanece humana."
   ],
   "em_aberto": {
    "texto": "A entrada do arquiteto e a camada de autoria. Como o arquiteto entra após a venda do gêmeo digital, preservando os direitos e a autoria do projeto, sem que a etapa humana se torne o gargalo da escala. Em aberto. O reconhecimento “isto é Nidum” em escala. Se pelo olhar do Comitê Técnico, por uma comunidade ampliada ou com apoio da inteligência artificial — como obter o olhar humano sem depender do esforço físico humano antes das camadas sensíveis. Em aberto. A conexão entre Forma e Fluxo. Como se dá, na prática, a presença do Comitê Executivo no Comitê Técnico no momento em que a forma acontece, e como o método se desenha participando dos MVPs. Em aberto. A carta que carrega o DNA. A primeira versão existe; falta refiná-la até que baste, sozinha, para que qualquer projeto nasça fiel ao DNA e aos valores, sem controle central. Em aberto. O lead time e o grau de automação. Quanto se pode reduzir o tempo da célula e até onde a automação substitui a mão humana antes das etapas sensíveis do processo. Em aberto.",
    "itens": [
     {
      "tema": "A entrada do arquiteto e a camada de autoria",
      "texto": "A entrada do arquiteto e a camada de autoria. Como o arquiteto entra após a venda do gêmeo digital, preservando os direitos e a autoria do projeto, sem que a etapa humana se torne o gargalo da escala. Em aberto."
     },
     {
      "tema": "O reconhecimento “isto é Nidum” em escala",
      "texto": "O reconhecimento “isto é Nidum” em escala. Se pelo olhar do Comitê Técnico, por uma comunidade ampliada ou com apoio da inteligência artificial — como obter o olhar humano sem depender do esforço físico humano antes das camadas sensíveis. Em aberto."
     },
     {
      "tema": "A conexão entre Forma e Fluxo",
      "texto": "A conexão entre Forma e Fluxo. Como se dá, na prática, a presença do Comitê Executivo no Comitê Técnico no momento em que a forma acontece, e como o método se desenha participando dos MVPs. Em aberto."
     },
     {
      "tema": "A carta que carrega o DNA",
      "texto": "A carta que carrega o DNA. A primeira versão existe; falta refiná-la até que baste, sozinha, para que qualquer projeto nasça fiel ao DNA e aos valores, sem controle central. Em aberto."
     },
     {
      "tema": "O lead time e o grau de automação",
      "texto": "O lead time e o grau de automação. Quanto se pode reduzir o tempo da célula e até onde a automação substitui a mão humana antes das etapas sensíveis do processo. Em aberto."
     }
    ]
   },
   "proximo_passo": "Concluir o ciclo atual de convergências dos produtos e, em seguida, dar foco ao campo: iniciar o planejamento do primeiro MVP — o apartamento do Rio de Janeiro — como célula inicial a validar passo a passo e a desdobrar às plataformas regionais; e levar ao Comitê Técnico, em sua reunião inicial com os arquitetos, a calibração da entrada do arquiteto, da carta que carrega o DNA e da conexão entre a Forma e o Fluxo."
  }
 ],
 "Comunidades Vivas": [
  {
   "prefixo": "CVI",
   "ecossistema": "Comunidades Vivas",
   "data_iso": "2026-05-21",
   "data_br": "21/5/2026",
   "arquivo": "CVI_Convergencia_21052026_v1.pdf",
   "movimentos": [
    "Não é loteamento. Não é filantropia. É um organismo vivo.",
    "A fonte é quem vai morar ali. Não o projeto arquitetônico.",
    "A transformação real nasce da cultura, do vínculo e do protagonismo."
   ],
   "em_aberto": {
    "texto": "O perfil de quem entra — alinhamento antes de moradia. Como identificar e reunir as pessoas que querem aquilo, não apenas precisam de moradia, sem que o critério vire exclusão. O alinhamento de propósito é o que constrói comunidade — mas o método de seleção ainda não foi desenhado. Em aberto. A escala da primeira Comunidade Viva em Londrina. Quantas casas, que mix de tamanhos e tipos, que ritmo de construção e formação. Londrina é a possibilidade concreta, mas a dimensão e o faseamento ainda não foram definidos. Em aberto. O equilíbrio entre espaço privado e espaço comum. Quanto do território é casa e quanto é praça, biblioteca, convivência — onde o organismo respira. O princípio está claro; a proporção concreta, não. Em aberto.",
    "itens": [
     {
      "tema": "O perfil de quem entra — alinhamento antes de moradia",
      "texto": "O perfil de quem entra — alinhamento antes de moradia. Como identificar e reunir as pessoas que querem aquilo, não apenas precisam de moradia, sem que o critério vire exclusão. O alinhamento de propósito é o que constrói comunidade — mas o método de seleção ainda não foi desenhado. Em aberto."
     },
     {
      "tema": "A escala da primeira Comunidade Viva em Londrina",
      "texto": "A escala da primeira Comunidade Viva em Londrina. Quantas casas, que mix de tamanhos e tipos, que ritmo de construção e formação. Londrina é a possibilidade concreta, mas a dimensão e o faseamento ainda não foram definidos. Em aberto."
     },
     {
      "tema": "O equilíbrio entre espaço privado e espaço comum",
      "texto": "O equilíbrio entre espaço privado e espaço comum. Quanto do território é casa e quanto é praça, biblioteca, convivência — onde o organismo respira. O princípio está claro; a proporção concreta, não. Em aberto."
     }
    ]
   },
   "proximo_passo": "Reunir as leituras de quem conhece de perto a regeneração de comunidades — método, não infraestrutura — e aprofundar o perfil de quem entra e a escala da primeira Comunidade Viva, para que o desenho de Londrina nasça do vínculo, não da planta."
  },
  {
   "prefixo": "CVI",
   "ecossistema": "Comunidades Vivas",
   "data_iso": "2026-06-08",
   "data_br": "8/6/2026",
   "arquivo": "CVI_Convergencia_08062026_v1.pdf",
   "movimentos": [
    "A imagem não foi imposta — emergiu de muitas vozes, e convergiu.",
    "Comunidade Viva é a vida acontecendo — não a infraestrutura entregue.",
    "Uma comunidade viva tem contorno — não muro.",
    "A fonte é quem vai morar ali — e a permanência é parte da obra."
   ],
   "em_aberto": {
    "texto": "O critério de convergência de valores. Como reunir quem quer aquilo — e não apenas precisa de moradia — sem que o alinhamento de propósito vire exclusão, preservando a mistura de renda e a porosidade. E como cuidar da dupla relação de quem mora e também trabalha, para que o vínculo não escorregue para dependência. Em aberto. A escuta que precede o desenho. Como conviver para conhecer de verdade quem vai habitar — suas necessidades reais — e quem conduz essa escuta, antes que a primeira imagem se feche em forma. Em aberto. A permanência da Academia e o modelo que a sustenta. Por quanto tempo e de que forma a presença formadora permanece, e como o serviço contínuo dos espaços comuns gera renda sem criar dependência nem tornar a Nidum o centro. Em aberto. A relação com o entorno e a especulação. Como construir as pontes de confiança com o que está em volta e, ao mesmo tempo, proteger o vivo de ser imitado como forma morta. Em aberto.",
    "itens": [
     {
      "tema": "O critério de convergência de valores",
      "texto": "O critério de convergência de valores. Como reunir quem quer aquilo — e não apenas precisa de moradia — sem que o alinhamento de propósito vire exclusão, preservando a mistura de renda e a porosidade. E como cuidar da dupla relação de quem mora e também trabalha, para que o vínculo não escorregue para dependência. Em aberto."
     },
     {
      "tema": "A escuta que precede o desenho",
      "texto": "A escuta que precede o desenho. Como conviver para conhecer de verdade quem vai habitar — suas necessidades reais — e quem conduz essa escuta, antes que a primeira imagem se feche em forma. Em aberto."
     },
     {
      "tema": "A permanência da Academia e o modelo que a sustenta",
      "texto": "A permanência da Academia e o modelo que a sustenta. Por quanto tempo e de que forma a presença formadora permanece, e como o serviço contínuo dos espaços comuns gera renda sem criar dependência nem tornar a Nidum o centro. Em aberto."
     },
     {
      "tema": "A relação com o entorno e a especulação",
      "texto": "A relação com o entorno e a especulação. Como construir as pontes de confiança com o que está em volta e, ao mesmo tempo, proteger o vivo de ser imitado como forma morta. Em aberto."
     }
    ]
   },
   "proximo_passo": "Levar este novo contorno de Comunidades Vivas ao desenho de um projeto — com a primeira imagem da inteligência como piso a ser superado —, mantendo a escuta de quem vai habitar como o verdadeiro início, para que a primeira Comunidade Viva nasça do vínculo e do propósito, e não da planta."
  },
  {
   "prefixo": "CVI",
   "ecossistema": "Comunidades Vivas",
   "data_iso": "2026-06-23",
   "data_br": "23/6/2026",
   "arquivo": "CVI_Convergencia_23062026_v1.pdf",
   "movimentos": [
    "Um loteamento que quer nascer organismo, não parcelamento.",
    "A comunidade vem antes do imóvel.",
    "O indicador que mede o que importa: o fim do abismo.",
    "A referência admirável, e a calibração do financiamento."
   ],
   "em_aberto": {
    "texto": "A natureza da referência e da parceria. Se o trabalho admirado entra como parceiro, coautor ou inspiração — e em que medida o seu método se integra ao loteamento de Londrina. Em aberto. O financiamento da comunidade. Como sustentar a Comunidade Viva pela própria engenharia — a Fazenda Viva sustentando a comunidade no mesmo projeto — sem depender de fomento público. Em aberto. Os indicadores da Comunidade Viva. Como traduzir distribuição de renda, redução do abismo de expectativa de vida e pertencimento em régua Nidum, sem reduzir a número o que só o reconhecimento humano enxerga. Em aberto. O gêmeo digital do loteamento. A engenharia inteira — viabilidade, fluxos, governança e a seleção de quem vai habitar e trabalhar — antes de qualquer obra física. Em aberto.",
    "itens": [
     {
      "tema": "A natureza da referência e da parceria",
      "texto": "A natureza da referência e da parceria. Se o trabalho admirado entra como parceiro, coautor ou inspiração — e em que medida o seu método se integra ao loteamento de Londrina. Em aberto."
     },
     {
      "tema": "O financiamento da comunidade",
      "texto": "O financiamento da comunidade. Como sustentar a Comunidade Viva pela própria engenharia — a Fazenda Viva sustentando a comunidade no mesmo projeto — sem depender de fomento público. Em aberto."
     },
     {
      "tema": "Os indicadores da Comunidade Viva",
      "texto": "Os indicadores da Comunidade Viva. Como traduzir distribuição de renda, redução do abismo de expectativa de vida e pertencimento em régua Nidum, sem reduzir a número o que só o reconhecimento humano enxerga. Em aberto."
     },
     {
      "tema": "O gêmeo digital do loteamento",
      "texto": "O gêmeo digital do loteamento. A engenharia inteira — viabilidade, fluxos, governança e a seleção de quem vai habitar e trabalhar — antes de qualquer obra física. Em aberto."
     }
    ]
   },
   "proximo_passo": "Aprofundar a intenção reta da Comunidade Viva de Londrina e desenhar o seu gêmeo digital — o organismo social com habitação, trabalho, formação, cultura e pertencimento, sua viabilidade, sua governança e a seleção das pessoas —, estudando a referência admirada como aprendizado e mantendo o horizonte da autossustentabilidade pela integração com a Fazenda Viva."
  }
 ],
 "Fazenda-âncora": [
  {
   "prefixo": "FAN",
   "ecossistema": "Fazenda-âncora",
   "data_iso": "2026-05-19",
   "data_br": "19/5/2026",
   "arquivo": "FAN_Convergencia_19052026_v1.pdf",
   "movimentos": [
    "A fazenda não é um ativo. É um centro de gravidade.",
    "Regeneração é o eixo, não um tema entre outros.",
    "Fazenda viva — não teatro, não simulação."
   ],
   "em_aberto": {
    "texto": "Qual é a vocação principal da fazenda? A reunião trouxe leituras fortes para caminhos diferentes: hotel-fazenda boutique, comunidade residencial com produção viva, turismo de aventura ancorado nos cânions da região, ecoterapia, turismo histórico. Nenhum se firmou como vocação primeira. Sem definir foco, o masterplan não tem onde se apoiar. Essa escolha provavelmente só se faz com uma visita ao território — não em sala. Gestão própria ou operação por concessão? A pergunta foi levantada diretamente: a Nidum administra o hotel-fazenda ou entrega a um operador? A inclinação da reunião foi pela gestão própria — para manter controle da filosofia, do desenvolvimento das pessoas, da integridade com o que se propõe construir. Mas não fechou. A questão segue em aberto. Escala e masterplan. A noite produziu muitas imagens, mas nenhuma dimensão. Quantos quartos? Quantas casas? Qual o peso de cada programa — residencial, hospedagem, produção, público externo? O masterplan foi identificado como necessário. Ainda não existe. Precisa de um primeiro desenho coletivo para que as soluções possam ser organizadas em camadas.",
    "itens": [
     {
      "tema": "Qual é a vocação principal da fazenda?",
      "texto": "Qual é a vocação principal da fazenda? A reunião trouxe leituras fortes para caminhos diferentes: hotel-fazenda boutique, comunidade residencial com produção viva, turismo de aventura ancorado nos cânions da região, ecoterapia, turismo histórico. Nenhum se firmou como vocação primeira. Sem definir foco, o masterplan não tem onde se apoiar. Essa escolha provavelmente só se faz com uma visita ao território — não em sala."
     },
     {
      "tema": "Gestão própria ou operação por concessão?",
      "texto": "Gestão própria ou operação por concessão? A pergunta foi levantada diretamente: a Nidum administra o hotel-fazenda ou entrega a um operador? A inclinação da reunião foi pela gestão própria — para manter controle da filosofia, do desenvolvimento das pessoas, da integridade com o que se propõe construir. Mas não fechou. A questão segue em aberto. Escala e masterplan. A noite produziu muitas imagens, mas nenhuma dimensão."
     },
     {
      "tema": "Quantos quartos?",
      "texto": "Quantos quartos?"
     },
     {
      "tema": "Quantas casas?",
      "texto": "Quantas casas? Qual o peso de cada programa — residencial, hospedagem, produção, público externo? O masterplan foi identificado como necessário. Ainda não existe. Precisa de um primeiro desenho coletivo para que as soluções possam ser organizadas em camadas."
     }
    ]
   },
   "proximo_passo": "Quem ainda não enviou sua leitura da Fazenda Fortaleza envia ao longo dos próximos dias — em texto, áudio, desenho, como vier. A próxima conversa continua de onde esta parou, com foco nas três questões em aberto acima. Uma visita ao território, quando possível, é o passo que mais pode mover a questão da vocação."
  },
  {
   "prefixo": "FAN",
   "ecossistema": "Fazenda-âncora",
   "data_iso": "2026-05-29",
   "data_br": "29/5/2026",
   "arquivo": "FAN_Convergencia_29052026_v2.pdf",
   "movimentos": [
    "A vocação não se inventa: lê-se na memória do território.",
    "A Fazenda é a Nidum em corpo — a expressão mais ampla do método.",
    "Hospitalidade é conteúdo, não estrutura — e o acolhimento começa antes da"
   ],
   "em_aberto": {
    "texto": "A segunda rodada avançou nas três questões que a primeira deixou abertas, mas nenhuma fechou em definitivo. A Fonte não as resolve. Seguem para a próxima conversa. A vocação principal — convergindo, ainda não fechada. A leitura forte da rodada foi a Fazenda como Comunidade Viva rural de amplitude máxima, abrigando hotel-fazenda, comunidade residencial com produção, Academia e experiência regenerativa ao mesmo tempo. É uma direção, não ainda uma escolha de foco primeiro. O masterplan depende dessa definição, e a visita ao território aparece como o passo que mais pode movê-la. Caminho jurídico do parcelamento em zona rural. A leitura legal preliminar indicou que loteamento urbano não se aplica em zona rural, mas há caminhos: condomínio de chácaras de recreio, parcelamento por módulo mínimo rural, associação de frações, ou unidades vinculadas a um hotel-fazenda. A legislação local admite usos por autorização excepcional, e a faixa lindeira à rodovia tem regime diferenciado. A modelagem exige diligência no local antes de fechar a forma. Modelo de operação do hotel-fazenda. A inclinação seguiu pela gestão própria, com a Academia formando a mão de obra dentro da cultura Nidum — mantendo controle da filosofia e do acolhimento. A parceria com um operador externo permanece como hipótese, desde que preserve esse alinhamento. Não fechou. Faseamento e capitalização. Levantou-se a pergunta sobre quando a Fazenda entra no cronograma — se depende de capitalização prévia ou avança em paralelo. A leitura da Fonte é que, havendo condições legais e ambientais resolvidas em prazo curto, o caminho é desenhar o gêmeo digital e abrir venda por valor percebido, faseando conforme a natureza do conjunto. A decisão de sequência fica para a modelagem.",
    "itens": [
     {
      "tema": "A vocação principal — convergindo, ainda não fechada",
      "texto": "A vocação principal — convergindo, ainda não fechada. A leitura forte da rodada foi a Fazenda como Comunidade Viva rural de amplitude máxima, abrigando hotel-fazenda, comunidade residencial com produção, Academia e experiência regenerativa ao mesmo tempo. É uma direção, não ainda uma escolha de foco primeiro. O masterplan depende dessa definição, e a visita ao território aparece como o passo que mais pode movê-la."
     },
     {
      "tema": "Caminho jurídico do parcelamento em zona rural",
      "texto": "Caminho jurídico do parcelamento em zona rural. A leitura legal preliminar indicou que loteamento urbano não se aplica em zona rural, mas há caminhos: condomínio de chácaras de recreio, parcelamento por módulo mínimo rural, associação de frações, ou unidades vinculadas a um hotel-fazenda. A legislação local admite usos por autorização excepcional, e a faixa lindeira à rodovia tem regime diferenciado. A modelagem exige diligência no local antes de fechar a forma."
     },
     {
      "tema": "Modelo de operação do hotel-fazenda",
      "texto": "Modelo de operação do hotel-fazenda. A inclinação seguiu pela gestão própria, com a Academia formando a mão de obra dentro da cultura Nidum — mantendo controle da filosofia e do acolhimento. A parceria com um operador externo permanece como hipótese, desde que preserve esse alinhamento. Não fechou."
     },
     {
      "tema": "Faseamento e capitalização",
      "texto": "Faseamento e capitalização. Levantou-se a pergunta sobre quando a Fazenda entra no cronograma — se depende de capitalização prévia ou avança em paralelo. A leitura da Fonte é que, havendo condições legais e ambientais resolvidas em prazo curto, o caminho é desenhar o gêmeo digital e abrir venda por valor percebido, faseando conforme a natureza do conjunto. A decisão de sequência fica para a modelagem."
     }
    ]
   },
   "proximo_passo": "Organizar a visita ao território como o gesto que destrava a vocação — sentir o lugar, a casa, a capela, os cânions, a escala real. Em paralelo, reunir a leitura histórico-simbólica (o resgate documental da memória da fazenda) e a leitura jurídica do parcelamento, para que o primeiro desenho de masterplan possa nascer apoiado em foco definido. Quem ainda não enviou sua leitura da Fazenda envia ao longo dos próximos dias — em texto, áudio ou desenho."
  },
  {
   "prefixo": "FAN",
   "ecossistema": "Fazenda-âncora",
   "data_iso": "2026-06-17",
   "data_br": "17/6/2026",
   "arquivo": "FAN_Convergencia_17062026_v1.pdf",
   "movimentos": [
    "A vocação se lê na memória do território — não se inventa.",
    "Travessia, pouso e escuta: a hospitalidade que regenera.",
    "Indivíduo, lugar e movimento — a Fonte, a Forma e o Fluxo do território.",
    "A integridade vem antes do projeto — e se vive antes de se vender."
   ],
   "em_aberto": {
    "texto": "A leitura de campo do território. A imersão presencial — percorrer a fazenda a pé, confirmar a poligonal com topógrafo e resolver as áreas de preservação — ainda não foi feita. Em aberto. A narrativa e os guardiões da memória. Como reunir, com historiadores, museus e a família, a profundidade histórica — tropeirismo, campos gerais, cultura cabocla e indígena — numa narrativa que ancore o projeto. Em aberto. Os artistas e os materiais do lugar. Como mapear, fora dos circuitos, quem trabalha a madeira, a lã e a gravura — o resgate que dá autenticidade à forma. Em aberto. O dimensionamento e o estudo de mercado. Quanto de cada produto — hotel, condomínio, destino — cabe nos cerca de 211 hectares, e como uma fazenda no centro do estado se posiciona como destino. Em aberto.",
    "itens": [
     {
      "tema": "A leitura de campo do território",
      "texto": "A leitura de campo do território. A imersão presencial — percorrer a fazenda a pé, confirmar a poligonal com topógrafo e resolver as áreas de preservação — ainda não foi feita. Em aberto."
     },
     {
      "tema": "A narrativa e os guardiões da memória",
      "texto": "A narrativa e os guardiões da memória. Como reunir, com historiadores, museus e a família, a profundidade histórica — tropeirismo, campos gerais, cultura cabocla e indígena — numa narrativa que ancore o projeto. Em aberto."
     },
     {
      "tema": "Os artistas e os materiais do lugar",
      "texto": "Os artistas e os materiais do lugar. Como mapear, fora dos circuitos, quem trabalha a madeira, a lã e a gravura — o resgate que dá autenticidade à forma. Em aberto."
     },
     {
      "tema": "O dimensionamento e o estudo de mercado",
      "texto": "O dimensionamento e o estudo de mercado. Quanto de cada produto — hotel, condomínio, destino — cabe nos cerca de 211 hectares, e como uma fazenda no centro do estado se posiciona como destino. Em aberto."
     }
    ]
   },
   "proximo_passo": "Formar um núcleo de trabalho dedicado e fazer a imersão presencial no território — lendo a sua memória com quem a guarda —, para destilar, com a inteligência híbrida, a Fonte da Fazenda-âncora numa narrativa e numa forma fiéis ao lugar, antes de dimensionar os produtos."
  }
 ],
 "Reunião geral": [
  {
   "prefixo": "GER",
   "ecossistema": "Reunião geral",
   "data_iso": "2026-06-25",
   "data_br": "25/6/2026",
   "arquivo": "GER_Convergencia_25062026_v1.pdf",
   "movimentos": [
    "A primeira reunião mensal, e onde a Nidum está agora.",
    "A intenção reta, e os quatro valores como quatro camadas de valor.",
    "Fonte, forma e fluxo: a célula íntegra e o organismo que se organiza.",
    "A engenharia econômica, e a régua 100/120 calibrada.",
    "O gêmeo digital: o produto, e onde o valor nasce.",
    "O tema que abriu o nervo: a autoria, o arquiteto e a inteligência coletiva.",
    "Os produtos, os pontos de gravidade, e a escala como tese."
   ],
   "em_aberto": {
    "texto": "A autoria na era da inteligência coletiva. Se a arquitetura Nidum será humana, coletiva ou híbrida, e em que medida — questão reservada ao Conselho Curador e ao Comitê Técnico, condicionada à prova de mercado e a um pilar firme de segurança e governança de dados. Em aberto. O gêmeo digital como bem negociável. Se o gêmeo digital pode ser comprado e vendido — a princípio entre coautores — e até onde a regeneração pode ser concebida no virtual antes de tocar o mundo físico. Em aberto. O modelo de suprimento e a fronteira da régua. Entre mão de obra própria e fornecedores de confiança a desenvolver, para reduzir intermediações artificiais; e o critério do que é significativo o bastante para um contribuinte entrar na régua 100/120, definido projeto a projeto. Em aberto. Os indicadores dos quatro valores. Como tornar beleza, bondade, justiça e verdade medíveis por indicadores claros, sem reduzir a número o que só o reconhecimento humano, atravessado pela intenção reta, enxerga. Em aberto.",
    "itens": [
     {
      "tema": "A autoria na era da inteligência coletiva",
      "texto": "A autoria na era da inteligência coletiva. Se a arquitetura Nidum será humana, coletiva ou híbrida, e em que medida — questão reservada ao Conselho Curador e ao Comitê Técnico, condicionada à prova de mercado e a um pilar firme de segurança e governança de dados. Em aberto."
     },
     {
      "tema": "O gêmeo digital como bem negociável",
      "texto": "O gêmeo digital como bem negociável. Se o gêmeo digital pode ser comprado e vendido — a princípio entre coautores — e até onde a regeneração pode ser concebida no virtual antes de tocar o mundo físico. Em aberto."
     },
     {
      "tema": "O modelo de suprimento e a fronteira da régua",
      "texto": "O modelo de suprimento e a fronteira da régua. Entre mão de obra própria e fornecedores de confiança a desenvolver, para reduzir intermediações artificiais; e o critério do que é significativo o bastante para um contribuinte entrar na régua 100/120, definido projeto a projeto. Em aberto."
     },
     {
      "tema": "Os indicadores dos quatro valores",
      "texto": "Os indicadores dos quatro valores. Como tornar beleza, bondade, justiça e verdade medíveis por indicadores claros, sem reduzir a número o que só o reconhecimento humano, atravessado pela intenção reta, enxerga. Em aberto."
     }
    ]
   },
   "proximo_passo": "Avançar a projetização das iniciativas e erguer os gêmeos digitais das primeiras matrizes — a fazenda-âncora e os ativos em retrofit — com viabilidade, fluxos, governança e a seleção das pessoas, para que, funcionando íntegras, possam ser replicadas em escala. E levar ao Conselho Curador e ao Comitê Técnico a questão da autoria na era da inteligência coletiva, ouvidos o mercado e o pilar de dados."
  }
 ],
 "Marketing e Posicionamento": [
  {
   "prefixo": "MKT",
   "ecossistema": "Marketing e Posicionamento",
   "data_iso": "2026-06-11",
   "data_br": "11/6/2026",
   "arquivo": "MKT_Convergencia_11062026_v1.pdf",
   "movimentos": [
    "O marketing não inventa a Nidum — ele a percebe e a traduz.",
    "Reconhecida, não anunciada: a confiança não se compra, constrói-se.",
    "A síntese verdadeira explica — e deixa um silêncio a ser preenchido.",
    "A inteligência amplia os sentidos; a fonte íntegra é que dá sentido."
   ],
   "em_aberto": {
    "texto": "A frase síntese. Encontrar a expressão que explica e instiga, fiel à Fonte e adaptável a cada interlocutor, sem limitar o que a Nidum é. A direção está clara; a frase, ainda em lapidação. Em aberto. O reposicionamento visual. A nova identidade — paleta inspirada nas cores e texturas do Brasil, e a eventual revisão tipográfica — segue em construção, com a primeira entrega de identidade já prevista. Em aberto. O lugar da inteligência híbrida na narrativa. Como falar dela como aliada que devolve humanidade, sem reforçar o preconceito nem o lugar-comum. Em aberto. As interfaces entre os ecossistemas. Como o marketing se conecta de fato a academia, produtos, plataforma, operações, finanças, jurídico e sustentabilidade — os fluxos de trabalho conjunto ainda a desenhar. Em aberto.",
    "itens": [
     {
      "tema": "A frase síntese",
      "texto": "A frase síntese. Encontrar a expressão que explica e instiga, fiel à Fonte e adaptável a cada interlocutor, sem limitar o que a Nidum é. A direção está clara; a frase, ainda em lapidação. Em aberto."
     },
     {
      "tema": "O reposicionamento visual",
      "texto": "O reposicionamento visual. A nova identidade — paleta inspirada nas cores e texturas do Brasil, e a eventual revisão tipográfica — segue em construção, com a primeira entrega de identidade já prevista. Em aberto."
     },
     {
      "tema": "O lugar da inteligência híbrida na narrativa",
      "texto": "O lugar da inteligência híbrida na narrativa. Como falar dela como aliada que devolve humanidade, sem reforçar o preconceito nem o lugar-comum. Em aberto."
     },
     {
      "tema": "As interfaces entre os ecossistemas",
      "texto": "As interfaces entre os ecossistemas. Como o marketing se conecta de fato a academia, produtos, plataforma, operações, finanças, jurídico e sustentabilidade — os fluxos de trabalho conjunto ainda a desenhar. Em aberto."
     }
    ]
   },
   "proximo_passo": "Lapidar a frase síntese e o reposicionamento a partir da escuta de toda a rede, entregar a nova identidade visual e a primeira presença pública (site e canais), e abrir as interfaces do marketing com os demais ecossistemas — sempre traduzindo a Fonte para o mercado sem traí-la, para que a marca seja reconhecida pela coerência, e não anunciada."
  }
 ],
 "Nidum Mundo": [
  {
   "prefixo": "MUN",
   "ecossistema": "Nidum Mundo",
   "data_iso": "2026-05-18",
   "data_br": "18/5/2026",
   "arquivo": "MUN_Convergencia_18052026_v1.pdf",
   "movimentos": [
    "O que distingue o Nidum Mundo não é o preço. É o vínculo.",
    "A casa fala a língua de quem vai habitá-la.",
    "O método se descobre no primeiro projeto, não antes."
   ],
   "em_aberto": {
    "texto": "\"Nidum Mundo\" é o nome certo? Se a casa fala a língua de cada cultura, talvez o produto não seja \"Mundo\" — e sim um convite específico por origem: Nidum Itália, Nidum Japão, Nidum Estados Unidos. O nome genérico pode contradizer o princípio do reconhecimento específico. Em aberto. Mundo e Brasil são dois produtos ou um com camadas diferentes? A reunião não enxergou diferença clara entre os dois pela faixa de preço. A hipótese que ficou: talvez o Mundo seja o mesmo ativo do Brasil com uma camada de acolhimento por cima — recepção, integração, concierge. A Fonte mantém quatro produtos com vocações distintas. Essa fronteira ainda não convergiu. Quem é o cliente do Mundo? Brasileiro com capital fora, estrangeiro com leitura cultural, ambos? A reunião reposicionou a pergunta: antes de assumir o que é valor para esse cliente, ir até ele e descobrir. Nenhuma persona foi validada. Em aberto.",
    "itens": [
     {
      "tema": "\"Nidum Mundo\" é o nome certo? Se a casa fala a língua de cada cultura, talvez o produto não seja \"Mundo\" — e sim um convite específico por origem: Nidum Itália, Nidum Japão, Nidum Estados Unidos",
      "texto": "\"Nidum Mundo\" é o nome certo? Se a casa fala a língua de cada cultura, talvez o produto não seja \"Mundo\" — e sim um convite específico por origem: Nidum Itália, Nidum Japão, Nidum Estados Unidos. O nome genérico pode contradizer o princípio do reconhecimento específico. Em aberto."
     },
     {
      "tema": "Mundo e Brasil são dois produtos ou um com camadas diferentes? A reunião não enxergou diferença clara entre os dois pela faixa de preço",
      "texto": "Mundo e Brasil são dois produtos ou um com camadas diferentes? A reunião não enxergou diferença clara entre os dois pela faixa de preço. A hipótese que ficou: talvez o Mundo seja o mesmo ativo do Brasil com uma camada de acolhimento por cima — recepção, integração, concierge. A Fonte mantém quatro produtos com vocações distintas. Essa fronteira ainda não convergiu. Quem é o cliente do Mundo? Brasileiro com capital fora, estrangeiro com leitura cultural, ambos? A reunião reposicionou a pergunta: antes de assumir o que é valor para esse cliente, ir até ele e descobrir. Nenhuma persona foi validada. Em aberto."
     }
    ]
   },
   "proximo_passo": "Quem ainda não enviou sua leitura do Nidum Mundo envia ao longo da semana — em texto, áudio, desenho, como vier. A próxima reunião continua de onde esta parou, com foco nas três questões em aberto acima."
  },
  {
   "prefixo": "MUN",
   "ecossistema": "Nidum Mundo",
   "data_iso": "2026-06-18",
   "data_br": "18/6/2026",
   "arquivo": "MUN_Convergencia_18062026_v1.pdf",
   "movimentos": [
    "O Nidum Mundo é o limiar — onde duas realidades se cruzam sem se fundir.",
    "Revelar o Brasil — sem apagá-lo, sem exagerá-lo, sem pedir desculpas por",
    "O valor não está no imóvel — está na relação.",
    "A confiança é o fluxo vital — e torna-se verificável pela visibilidade."
   ],
   "em_aberto": {
    "texto": "Um produto ou dois. Se Brasil e Mundo são um único produto com dois modos de entrega ou dois produtos distintos — e o que de fato os distingue: o espaço, o serviço ou o habitante. Em aberto. O território primário. Se o Rio de Janeiro deve ser o ponto de partida do Mundo — a cidade que o estrangeiro mais reconhece como Brasil — e em que medida. Em aberto. O alcance do Mundo. Até onde a lógica do Mundo se estende — moradia, refúgio de férias, investimento de renda e até comunidades de estrangeiros — sem virar uma definição que restringe. Em aberto. A plataforma e a desintermediação. Como mapear o processo do cadastro do ninho à primeira venda, e desenhar os critérios de qualificação e a engenharia que torna o acesso justo — sem que a Nidum se torne uma construtora. Em aberto.",
    "itens": [
     {
      "tema": "Um produto ou dois",
      "texto": "Um produto ou dois. Se Brasil e Mundo são um único produto com dois modos de entrega ou dois produtos distintos — e o que de fato os distingue: o espaço, o serviço ou o habitante. Em aberto."
     },
     {
      "tema": "O território primário",
      "texto": "O território primário. Se o Rio de Janeiro deve ser o ponto de partida do Mundo — a cidade que o estrangeiro mais reconhece como Brasil — e em que medida. Em aberto."
     },
     {
      "tema": "O alcance do Mundo",
      "texto": "O alcance do Mundo. Até onde a lógica do Mundo se estende — moradia, refúgio de férias, investimento de renda e até comunidades de estrangeiros — sem virar uma definição que restringe. Em aberto."
     },
     {
      "tema": "A plataforma e a desintermediação",
      "texto": "A plataforma e a desintermediação. Como mapear o processo do cadastro do ninho à primeira venda, e desenhar os critérios de qualificação e a engenharia que torna o acesso justo — sem que a Nidum se torne uma construtora. Em aberto."
     }
    ]
   },
   "proximo_passo": "Levar ao Comitê Técnico a convergência sobre um produto ou dois e sobre o território primário, e seguir nos pilotos físicos — mapeando o processo do cadastro à primeira venda —, para que a plataforma de relações que é a Nidum aprenda com o fazer, e o Nidum Mundo revele o Brasil a quem o escolheu, sem apagá-lo nem exagerá-lo."
  }
 ],
 "Operações": [
  {
   "prefixo": "OPE",
   "ecossistema": "Operações",
   "data_iso": "2026-06-01",
   "data_br": "1/6/2026",
   "arquivo": "OPE_Convergencia_01062026_v1.pdf",
   "movimentos": [
    "A pergunta que a reunião abriu: a Nidum executa a obra ou orquestra quem a",
    "A plataforma como inteligência que conecta — escala que não vem de braço,",
    "Workflow de arquitetura: o criador escala de duas mãos para dez.",
    "Critérios de entrada como guardiões da cultura — em toda a cadeia."
   ],
   "em_aberto": {
    "texto": "A reunião abriu mais do que fechou — e isso é próprio de um ecossistema que ainda desenha seu modo de operar. A Fonte orienta, mas não resolve estas questões. Executar a obra ou afiançar quem executa. A definição entre a Nidum como executora da obra em coautoria e a Nidum como plataforma que orquestra e afiança os atores segue aberta. A escolha muda o perfil societário, a responsabilidade técnica e o próprio contrato social. É decisão de identidade — convergência antes de forma jurídica. O workflow de arquitetura e a relação com os criadores. Como o pré-projeto gerado pela inteligência híbrida se concilia com a autoria, os direitos e a adequação ao gosto do cliente; e como criadores em diferentes estágios entram no modelo. Discussão a conduzir em conjunto entre Operações, o grupo de arquitetos internos e o Comitê Técnico. Critérios de entrada em toda a cadeia. A definição dos critérios — de ativo, cliente, criador e parceiro — que preservam a cultura e a integridade da rede. Identificados como necessários; ainda não formulados. Do físico ao digital — a leitura territorial e o gêmeo digital. Como construir internamente a capacidade de leitura territorial por dados e a produção de gêmeos digitais, e quando uma parceria de dados externa complementa. O caminho reconhecido é começar no físico para entender o processo e digitalizá-lo em seguida, sem perder o rumo da plataforma.",
    "itens": [
     {
      "tema": "Executar a obra ou afiançar quem executa",
      "texto": "Executar a obra ou afiançar quem executa. A definição entre a Nidum como executora da obra em coautoria e a Nidum como plataforma que orquestra e afiança os atores segue aberta. A escolha muda o perfil societário, a responsabilidade técnica e o próprio contrato social. É decisão de identidade — convergência antes de forma jurídica."
     },
     {
      "tema": "O workflow de arquitetura e a relação com os criadores",
      "texto": "O workflow de arquitetura e a relação com os criadores. Como o pré-projeto gerado pela inteligência híbrida se concilia com a autoria, os direitos e a adequação ao gosto do cliente; e como criadores em diferentes estágios entram no modelo. Discussão a conduzir em conjunto entre Operações, o grupo de arquitetos internos e o Comitê Técnico."
     },
     {
      "tema": "Critérios de entrada em toda a cadeia",
      "texto": "Critérios de entrada em toda a cadeia. A definição dos critérios — de ativo, cliente, criador e parceiro — que preservam a cultura e a integridade da rede. Identificados como necessários; ainda não formulados."
     },
     {
      "tema": "Do físico ao digital — a leitura territorial e o gêmeo digital",
      "texto": "Do físico ao digital — a leitura territorial e o gêmeo digital. Como construir internamente a capacidade de leitura territorial por dados e a produção de gêmeos digitais, e quando uma parceria de dados externa complementa. O caminho reconhecido é começar no físico para entender o processo e digitalizá-lo em seguida, sem perder o rumo da plataforma."
     }
    ]
   },
   "proximo_passo": "Levar a pergunta de identidade — executar ou afiançar — ao caminho de convergência, porque dela dependem o contrato social e o desenho da plataforma. Em paralelo, Operações, arquitetos e Comitê Técnico desenham juntos o workflow de arquitetura e os critérios de entrada, e a plataforma tecnológica avança na leitura territorial e no gêmeo digital do primeiro ativo em estudo — para que a plataforma seja, desde o início, espelho fiel do que acontece na operação."
  }
 ],
 "Sustentabilidade": [
  {
   "prefixo": "SUS",
   "ecossistema": "Sustentabilidade",
   "data_iso": "2026-05-22",
   "data_br": "22/5/2026",
   "arquivo": "SUS_Convergencia_22052026_v1.pdf",
   "movimentos": [
    "Sustentabilidade não é atributo. É forma de ser. E para a Nidum, a palavra",
    "O ninho como resposta — material local, mão de obra local, conexão com o",
    "Integridade como fundamento — verdade em cada escolha, da cadeia ao"
   ],
   "em_aberto": {
    "texto": "Como a regeneração se torna mensurável sem virar certificação vazia. A reunião recusou o greenwashing e a métrica de fachada, mas reconheceu que a regeneração precisa ser verificável de algum modo. Como medir devolver integridade ao sistema sem cair no jogo de selos que a própria reunião criticou. Em aberto. O papel das Unidades Produtivas na cadeia de material local. Como estruturar a produção regional de material para fechar o ciclo de forma econômica e replicável. O princípio está claro; o desenho operacional das Unidades Produtivas, não. Em aberto. A coautoria com o cliente como prática de sustentabilidade. Como ensinar quem vai habitar a participar do processo de fazer, não só de escolher, em escala. O verbo fazer no centro é a tese; o método concreto de envolver o morador ainda não foi desenhado. Em aberto.",
    "itens": [
     {
      "tema": "Como a regeneração se torna mensurável sem virar certificação vazia",
      "texto": "Como a regeneração se torna mensurável sem virar certificação vazia. A reunião recusou o greenwashing e a métrica de fachada, mas reconheceu que a regeneração precisa ser verificável de algum modo. Como medir devolver integridade ao sistema sem cair no jogo de selos que a própria reunião criticou. Em aberto."
     },
     {
      "tema": "O papel das Unidades Produtivas na cadeia de material local",
      "texto": "O papel das Unidades Produtivas na cadeia de material local. Como estruturar a produção regional de material para fechar o ciclo de forma econômica e replicável. O princípio está claro; o desenho operacional das Unidades Produtivas, não. Em aberto."
     },
     {
      "tema": "A coautoria com o cliente como prática de sustentabilidade",
      "texto": "A coautoria com o cliente como prática de sustentabilidade. Como ensinar quem vai habitar a participar do processo de fazer, não só de escolher, em escala. O verbo fazer no centro é a tese; o método concreto de envolver o morador ainda não foi desenhado. Em aberto."
     }
    ]
   },
   "proximo_passo": "Aprofundar como a regeneração se torna verificável sem virar selo vazio, e desenhar o papel das Unidades Produtivas na cadeia de material local — para que sustentabilidade deixe de ser área e seja, de fato, a forma de operar de toda a Nidum."
  },
  {
   "prefixo": "SUS",
   "ecossistema": "Sustentabilidade",
   "data_iso": "2026-06-09",
   "data_br": "9/6/2026",
   "arquivo": "SUS_Convergencia_09062026_v1.pdf",
   "movimentos": [
    "Mais do que sustentar: regenerar — devolver mais integridade do que havia.",
    "A eficiência é uma forma de cuidado — e o cuidado é a raiz da",
    "O reconhecimento não se autodeclara — emerge da visibilidade e da relação.",
    "Regenerar é nascer de novo — a partir do ponto de integridade do lugar."
   ],
   "em_aberto": {
    "texto": "As certificações e o selo próprio. Quais certificações — corporativa e ambientais — mapear e adotar como referência desde a origem, e se a Nidum deve criar o seu próprio selo, para obras e fornecedores. Em aberto. A governança da inteligência. Como medir e conter a pegada do uso de inteligência — energia, água —, com diretrizes de uso eficiente e, talvez, um indicador do consumo e da economia gerada. Em aberto. A jornada e a idoneidade do fornecedor. Como selecionar, aculturar e acompanhar os fornecedores ao longo do tempo, garantindo alinhamento de valores e de práticas — e quem, na Nidum, cuida disso. Em aberto. Os sinais vitais do organismo. Quais indicadores acompanham a saúde da Nidum — econômicos, sociais e ambientais —, à maneira dos exames de um organismo vivo. Em aberto.",
    "itens": [
     {
      "tema": "As certificações e o selo próprio",
      "texto": "As certificações e o selo próprio. Quais certificações — corporativa e ambientais — mapear e adotar como referência desde a origem, e se a Nidum deve criar o seu próprio selo, para obras e fornecedores. Em aberto."
     },
     {
      "tema": "A governança da inteligência",
      "texto": "A governança da inteligência. Como medir e conter a pegada do uso de inteligência — energia, água —, com diretrizes de uso eficiente e, talvez, um indicador do consumo e da economia gerada. Em aberto."
     },
     {
      "tema": "A jornada e a idoneidade do fornecedor",
      "texto": "A jornada e a idoneidade do fornecedor. Como selecionar, aculturar e acompanhar os fornecedores ao longo do tempo, garantindo alinhamento de valores e de práticas — e quem, na Nidum, cuida disso. Em aberto."
     },
     {
      "tema": "Os sinais vitais do organismo",
      "texto": "Os sinais vitais do organismo. Quais indicadores acompanham a saúde da Nidum — econômicos, sociais e ambientais —, à maneira dos exames de um organismo vivo. Em aberto."
     }
    ]
   },
   "proximo_passo": "Mapear as certificações de referência e transformar a base teórica e prática de sustentabilidade em diretrizes por produto e por obra, levando o cuidado a cada elo da cadeia — para que a regeneração não seja um selo a alcançar, mas o metabolismo de tudo o que a Nidum faz."
  }
 ],
 "Plataforma Tecnológica": [
  {
   "prefixo": "TEC",
   "ecossistema": "Plataforma Tecnológica",
   "data_iso": "2026-05-23",
   "data_br": "23/5/2026",
   "arquivo": "TEC_Convergencia_23052026_v1.pdf",
   "movimentos": [
    "A plataforma em três corpos — um único lugar para tudo que a Nidum é e faz.",
    "A Fonte como centro irradiador — tudo entra pelo Conselho, tudo sai pela",
    "As jornadas não são lineares — e os agentes acompanham em qualquer"
   ],
   "em_aberto": {
    "texto": "As etapas definitivas de cada jornada de produto. A jornada de 13 etapas apresentada foi ilustrativa — não está validada. As etapas reais de cada produto (Mundo, Brasil, Fazenda-âncora, Comunidades Vivas) dependem das convergências que os ecossistemas de produto ainda estão construindo. Enquanto essas convergências não fecharem, as jornadas da plataforma permanecem como esqueleto. Em aberto. A jornada de intenção — o protótipo que não foi apresentado. O ecossistema desenvolveu um protótipo da jornada de intenção — como o morador chega à plataforma antes de qualquer cadastro, como a escuta acontece antes da proposta. Foi proposto compartilhar sem spoiler para cada coautor reagir sem viés. Ainda não foi visto pelo grupo. Em aberto. O nível de permissão e governança de cada perfil. A definição de quem edita o quê, a taxonomia de pastas e as convenções de nomenclatura — o desenho fino das permissões que controlam edição, não acesso. Reservado para a governança interna. Em aberto.",
    "itens": [
     {
      "tema": "As etapas definitivas de cada jornada de produto",
      "texto": "As etapas definitivas de cada jornada de produto. A jornada de 13 etapas apresentada foi ilustrativa — não está validada. As etapas reais de cada produto (Mundo, Brasil, Fazenda-âncora, Comunidades Vivas) dependem das convergências que os ecossistemas de produto ainda estão construindo. Enquanto essas convergências não fecharem, as jornadas da plataforma permanecem como esqueleto. Em aberto."
     },
     {
      "tema": "A jornada de intenção — o protótipo que não foi apresentado",
      "texto": "A jornada de intenção — o protótipo que não foi apresentado. O ecossistema desenvolveu um protótipo da jornada de intenção — como o morador chega à plataforma antes de qualquer cadastro, como a escuta acontece antes da proposta. Foi proposto compartilhar sem spoiler para cada coautor reagir sem viés. Ainda não foi visto pelo grupo. Em aberto."
     },
     {
      "tema": "O nível de permissão e governança de cada perfil",
      "texto": "O nível de permissão e governança de cada perfil. A definição de quem edita o quê, a taxonomia de pastas e as convenções de nomenclatura — o desenho fino das permissões que controlam edição, não acesso. Reservado para a governança interna. Em aberto."
     }
    ]
   },
   "proximo_passo": "Concluir as convergências dos ecossistemas de produto para que as jornadas da plataforma deixem de ser esqueleto e ganhem etapas reais, apresentar a jornada de intenção ao grupo e definir, com a governança, os perfis de permissão e a taxonomia."
  }
 ]
}""")

# ecossistema (entrada do usuário) -> (nome na Fonte p/ roster, nome na convergência)
ECO_RESOLVE = [
    (
        ("comunidades vivas", "comunidade viva", "cvi"),
        "Nidum Comunidades Vivas",
        "Comunidades Vivas",
    ),
    (
        ("fazenda", "âncora", "ancora", "fan", "fazendas vivas"),
        "Nidum Fazendas Vivas",
        "Fazenda-âncora",
    ),
    (("brasil", "bra"), "Nidum Brasil", "Nidum Brasil"),
    (("mundo", "mun"), "Nidum Mundo", "Nidum Mundo"),
    (("operações", "operacoes", "operação", "ope"), "Operações", "Operações"),
    (("sustentabilidade", "sus"), "Sustentabilidade", "Sustentabilidade"),
    (
        ("plataforma", "tecnológica", "tecnologica", "tecnologia", "tec"),
        "Plataforma Tecnológica",
        "Plataforma Tecnológica",
    ),
    (("academia", "aca"), "Academia Nidum", "Academia Nidum"),
    (
        ("marketing", "posicionamento", "mkt"),
        "Marketing e Posicionamento",
        "Marketing e Posicionamento",
    ),
]


class Tools:
    def __init__(self):
        pass

    # ---------- infra ----------
    def _d(self):
        return FONTE_INDEX

    def _di(self):
        return set(self._d().get("dedicacao_intensiva", []))

    def _fonte(self):
        return self._d().get("fonte", "Documento Fundador")

    @staticmethod
    def _clean(n):
        return re.sub(r"\s*\(.*?\)", "", n).strip()

    def _mk(self, name):
        return name + (" *" if self._clean(name) in self._di() else "")

    def _fmt_eco(self, e):
        prot = (
            ", ".join(self._mk(p) for p in e["protagonistas"])
            if e["protagonistas"]
            else "—"
        )
        return f"- {e['nome']} — Facilita: {self._mk(e['facilita'])}. Protagonistas: {prot}"

    def _find_eco(self, fonte_nome):
        for grp in (
            "ecossistemas_funcionais",
            "ecossistemas_produto",
            "ecossistemas_estruturais",
        ):
            for e in self._d()[grp]:
                if e["nome"] == fonte_nome:
                    return e
        return None

    def _resolve(self, q):
        ql = (q or "").lower()
        for chaves, fe, ce in ECO_RESOLVE:
            if any(re.search(r"\b" + re.escape(k) + r"\b", ql) for k in chaves):
                return fe, ce
        return None, None

    # ========== CAMADA 1 — FONTE: roster ==========
    def quadro_de_pessoas(self) -> str:
        """
        Retorna o quadro NOMINAL COMPLETO de quem compõe a Nidum, por órgão e ecossistema (facilitador + protagonistas), marcando quem está em dedicação intensiva. Chame SEMPRE que perguntarem, em QUALQUER frase, quem são os membros, as pessoas, os coautores, o time, a equipe, o quadro, a rede, quem faz parte ou participa da Nidum. Entregue a saída COMPLETA como ela vem (já etiquetada); NÃO resuma nem responda de memória/RAG.
        """
        d = self._d()
        L = [
            f"[Fonte — {d['fonte']}]",
            "",
            f"Membros da Nidum (índice de {d['atualizado_em']}), por órgão e ecossistema:",
            "",
        ]
        org, notas = d["orgaos"], d.get("notas", {})
        L += ["**Órgãos de governança**"]
        cc, ct, ce = (
            org.get("Conselho Curador"),
            org.get("Comitê Técnico"),
            org.get("Comitê Executivo"),
        )
        if cc:
            n = f" ({notas['Conselho Curador']})" if "Conselho Curador" in notas else ""
            L.append(
                f"- Conselho Curador — facilita {cc['facilitador']}. Membros: {', '.join(self._mk(m) for m in cc['membros'])}.{n}"
            )
        if ct:
            n = f" ({notas['Comitê Técnico']})" if "Comitê Técnico" in notas else ""
            L.append(
                f"- Comitê Técnico — facilita {ct['facilitador']}. Membros: {', '.join(self._mk(m) for m in ct['membros'])}.{n}"
            )
        if ce:
            L.append(
                f"- Comitê Executivo — facilitador permanente {ce['facilitador_permanente']}. Membros: {', '.join(self._mk(m) for m in ce['membros'])}."
            )
        L += ["", "**Ecossistemas funcionais**"] + [
            self._fmt_eco(e) for e in d["ecossistemas_funcionais"]
        ]
        L += ["", "**Ecossistemas de produto**"] + [
            self._fmt_eco(e) for e in d["ecossistemas_produto"]
        ]
        L += ["", "**Ecossistemas estruturais**"] + [
            self._fmt_eco(e) for e in d["ecossistemas_estruturais"]
        ]
        L += [
            "",
            f"\\* dedicação intensiva ({len(self._di())} coautores). Papéis são função, não cargo; cada coautor transita por vários ecossistemas.",
        ]
        return "\n".join(L)

    def dedicacao_intensiva(self) -> str:
        """
        Retorna a LISTA NOMINAL de quem está em dedicação intensiva (o núcleo que sustenta a operação no dia a dia). Use SEMPRE que perguntarem quem está/quem são em dedicação intensiva. Responda direto com os nomes.
        """
        d = self._d()
        di = d.get("dedicacao_intensiva", [])
        if not di:
            return "A lista de dedicação intensiva não está no índice."
        return (
            f"[Fonte — {d['fonte']}]\nEm dedicação intensiva — {len(di)} coautores:\n"
            + ", ".join(di)
            + "."
        )

    def pessoas_do_ecossistema(self, ecossistema: str) -> str:
        """
        Retorna o facilitador e os protagonistas de UM ecossistema ou órgão específico.
        :param ecossistema: nome do ecossistema/órgão (ex.: 'Operações', 'Nidum Brasil', 'Comitê Técnico').
        """
        d = self._d()
        alvo = ecossistema.strip().lower()
        for grp in (
            "ecossistemas_funcionais",
            "ecossistemas_produto",
            "ecossistemas_estruturais",
        ):
            for e in d[grp]:
                if alvo in e["nome"].lower():
                    return f"[Fonte — {d['fonte']}]\n" + self._fmt_eco(e)[2:]
        for nome, o in d["orgaos"].items():
            if alvo in nome.lower():
                fac = o.get("facilitador") or o.get("facilitador_permanente")
                return f"[Fonte — {d['fonte']}]\n{nome} — facilita {fac}. Membros: {', '.join(self._mk(m) for m in o.get('membros', []))}"
        return f"Não encontrei o ecossistema/órgão '{ecossistema}' no índice."

    def papeis_de_uma_pessoa(self, nome: str) -> str:
        """
        Retorna todos os ecossistemas/órgãos em que uma pessoa atua, o papel, e se está em dedicação intensiva.
        :param nome: nome ou parte do nome (ex.: 'Rachel', 'Pedro Shima').
        """
        d = self._d()
        alvo = nome.strip().lower()
        achados = []
        for grp in (
            "ecossistemas_funcionais",
            "ecossistemas_produto",
            "ecossistemas_estruturais",
        ):
            for e in d[grp]:
                if e["facilita"] and alvo in e["facilita"].lower():
                    achados.append(f"{e['nome']} (facilita)")
                elif any(alvo in p.lower() for p in e["protagonistas"]):
                    achados.append(f"{e['nome']} (protagonista)")
        for nome_org, o in d["orgaos"].items():
            fac = o.get("facilitador") or o.get("facilitador_permanente") or ""
            if (
                any(alvo in m.lower() for m in o.get("membros", []))
                or alvo in fac.lower()
            ):
                achados.append(
                    f"{nome_org} ({'facilitador' if alvo in fac.lower() else 'membro'})"
                )
        if not achados:
            return f"Não encontrei '{nome}' no índice da Fonte."
        di = (
            " — em dedicação intensiva"
            if any(alvo in p.lower() for p in d.get("dedicacao_intensiva", []))
            else ""
        )
        return (
            f"[Fonte — {d['fonte']}]\n{nome} atua em: " + "; ".join(achados) + di + "."
        )

    # ========== CAMADA 1 — FONTE: listas canônicas ==========
    def caminho_da_obra(self) -> str:
        """
        Retorna as ETAPAS do caminho da obra Nidum (a espiral), completas e em ordem. Use SEMPRE que perguntarem as etapas/passos/fases do caminho da obra, da jornada do ativo ou do projeto — em qualquer frase. Entregue TODAS, nunca um recorte.
        """
        et = self._d().get("caminho_da_obra", [])
        if not et:
            return "As etapas não estão no índice."
        linhas = "\n".join(f"{i}. {n}" for i, n in enumerate(et, 1))
        return f"[Fonte — {self._fonte()}]\nO caminho da obra Nidum — {len(et)} etapas (uma espiral, da originação ao acompanhamento):\n{linhas}"

    def principios_economicos(self) -> str:
        """
        Retorna os PRINCÍPIOS econômicos inegociáveis da Nidum, completos. Use quando perguntarem os princípios econômicos/financeiros, as regras inegociáveis da economia Nidum.
        """
        p = self._d().get("principios_economicos", [])
        if not p:
            return "Os princípios não estão no índice."
        return (
            f"[Fonte — {self._fonte()}]\nA economia da Nidum se sustenta em {len(p)} princípios inegociáveis:\n"
            + "\n".join(p)
        )

    def valores(self) -> str:
        """
        Retorna os VALORES da Nidum. Use quando perguntarem os valores, os pilares de valor.
        """
        v = self._d().get("valores", [])
        if not v:
            return "Os valores não estão no índice."
        return (
            f"[Fonte — {self._fonte()}]\nOs valores da Nidum, tomados ao pé da letra como camadas de valor real: "
            + ", ".join(v)
            + "."
        )

    def regua_de_valor(self) -> str:
        """
        Retorna a régua de valor (100/120) da Nidum. Use quando perguntarem como funciona a régua, a precificação por contribuição, o 100/120.
        """
        r = self._d().get("regua", "")
        if not r:
            return "A régua não está no índice."
        return f"[Fonte — {self._fonte()}]\n{r}"

    # ========== CAMADA 2 — CONVERGÊNCIAS: estado vigente (camada viva) ==========
    def estado_do_ecossistema(self, ecossistema: str) -> str:
        """
        Retorna o ESTADO VIGENTE de um ecossistema — a camada viva. Junta a base da Fonte (princípio fundador + quem sustenta) com TUDO que convergiu nas reuniões (em ordem) e o que segue em aberto. Use SEMPRE que perguntarem como está / em que pé está / o que há sobre um ecossistema ou frente (ex.: 'como está Comunidades Vivas', 'o que rolou na Fazenda', 'me atualiza sobre o Brasil') SEM citar uma data específica — a resposta deve ser o estado atual, não só a definição de origem.
        :param ecossistema: nome ou apelido do ecossistema (ex.: 'Comunidades Vivas', 'Fazenda', 'Brasil', 'Plataforma').
        """
        fe, ce = self._resolve(ecossistema)
        if not ce:
            return f"Não reconheci o ecossistema '{ecossistema}'. Ecossistemas: Comunidades Vivas, Fazenda-âncora, Nidum Brasil, Nidum Mundo, Operações, Sustentabilidade, Plataforma Tecnológica, Academia Nidum, Marketing e Posicionamento."
        convs = CONV_INDEX.get(ce, [])
        ultima = convs[-1]["data_br"] if convs else "—"
        L = [f"[Estado vigente — {ce} · Fonte + convergências até {ultima}]", ""]
        # base na Fonte
        e = self._find_eco(fe)
        L.append("**A base na Fonte** (o princípio, do Documento Fundador)")
        if e:
            prot = (
                ", ".join(self._mk(p) for p in e["protagonistas"])
                if e["protagonistas"]
                else "—"
            )
            L.append(
                f"Quem sustenta: facilita {self._mk(e['facilita'])}; protagonistas {prot}."
            )
        L.append(
            "A Fonte funda a intenção e o método; as convergências abaixo dão forma — nunca a substituem."
        )
        # convergências em ordem
        if convs:
            L += [
                "",
                "**O que convergiu, por reunião** (a forma que a rede deu, em ordem)",
            ]
            for c in convs:
                movs = (
                    "; ".join(c["movimentos"])
                    if c["movimentos"]
                    else "(registro da reunião)"
                )
                L.append(
                    f"- {c['data_br']} [Convergência · {ce} · {c['data_br']}]: {movs}"
                )
            # abertos consolidados, mais recente primeiro
            abertos = []
            for c in reversed(convs):
                for it in c["em_aberto"]["itens"]:
                    abertos.append(f"- {it['tema']} (desde {c['data_br']})")
            if abertos:
                L += ["", "**O que segue em aberto** (mais recente primeiro)"] + abertos
            prox = next(
                (c["proximo_passo"] for c in reversed(convs) if c.get("proximo_passo")),
                "",
            )
            if prox:
                L += ["", f"**Próximo passo** (da última convergência): {prox}"]
        else:
            L += [
                "",
                "Ainda não há convergência registrada para este ecossistema — vale a base da Fonte acima.",
            ]
        return "\n".join(L)

    def abertos_da_rede(self) -> str:
        """
        Retorna TODOS os temas em aberto da rede, por ecossistema (o que as convergências deixaram em definição). Use quando perguntarem o que está em aberto na Nidum, o que falta decidir, os pontos em definição.
        """
        L = ["[Convergências — pontos em aberto da rede]", ""]
        for eco in sorted(CONV_INDEX):
            itens = []
            for c in CONV_INDEX[eco]:
                for it in c["em_aberto"]["itens"]:
                    itens.append(f"  - {it['tema']} ({c['data_br']})")
            if itens:
                L.append(f"**{eco}**")
                L += itens
                L.append("")
        return "\n".join(L).strip()

    # ========== CAMADA 1 — FONTE: prosa (ponteiro de seção) ==========
    def buscar_na_fonte(self, tema: str) -> str:
        """
        Aponta a seção do Documento Fundador mais ligada a um tema conceitual (Fonte/Forma/Fluxo, integridade, inteligência híbrida, patologias, valor percebido etc.) para a resposta se ancorar nela. Use para perguntas conceituais sobre a filosofia/estrutura da Nidum.
        :param tema: o assunto (ex.: 'inteligência híbrida', 'integridade', 'patologias').
        """
        secoes = self._d().get("secoes", [])
        toks = [t for t in re.findall(r"\w{4,}", (tema or "").lower())]
        best, score = None, 0
        for s in secoes:
            txt = (s["parte"] + " " + s.get("lead", "")).lower()
            sc = sum(txt.count(t) for t in toks)
            if sc > score:
                best, score = s, sc
        if not best:
            return "Não localizei uma seção para esse tema."
        return f"[Fonte — {self._fonte()}]\nSeção mais ligada a '{tema}': {best['parte']}.\n{best.get('lead','')}"


# ============ ROTEADOR SEMÂNTICO (Filter) ============
INTENTS = {
    "roster": [
        "quem são os membros da Nidum",
        "quem são os coautores",
        "me lista as pessoas da Nidum",
        "qual é o time da Nidum",
        "quem faz parte da rede",
        "quem participa da Nidum",
        "quero o quadro de pessoas",
        "quem compõe a Nidum",
        "quais são as pessoas do grupo",
    ],
    "dedicacao": [
        "quem está em dedicação intensiva",
        "quem é o núcleo de dedicação intensiva",
        "lista do grupo de dedicação intensiva",
        "quem está full time",
        "quem são os DI",
        "quem sustenta a operação no dia a dia",
    ],
    "ecossistema": [
        "quem participa de operações",
        "quem está no ecossistema de comunidades vivas",
        "o time de marketing e posicionamento",
        "quem faz parte do comitê técnico",
        "membros de nidum brasil",
        "quem são as pessoas de sustentabilidade",
    ],
    "pessoa": [
        "quem é a Rachel Berrutti",
        "onde o Pedro Shima atua",
        "o que o Thiago Trindade faz",
        "em quais ecossistemas a Gabriela está",
        "qual o papel do Daniel Bisol",
    ],
    "caminho_obra": [
        "quais são as etapas do caminho da obra",
        "quantas etapas tem a jornada do ativo",
        "me lista as fases do projeto Nidum",
        "quais os passos da obra",
        "as etapas da espiral",
        "como é o caminho de uma obra do começo ao fim",
    ],
    "principios": [
        "quais são os princípios econômicos",
        "as regras inegociáveis da economia Nidum",
        "os princípios financeiros da Nidum",
        "quais princípios sustentam a economia",
    ],
    "valores": [
        "quais são os valores da Nidum",
        "os pilares de valor",
        "beleza bondade justiça verdade",
    ],
    "regua": [
        "como funciona a régua de valor",
        "o que é o 100/120",
        "como a contribuição é precificada",
        "a régua 100 120 da Nidum",
    ],
    "estado_eco": [
        "como está comunidades vivas",
        "em que pé está a fazenda",
        "me atualiza sobre o nidum brasil",
        "o que há de novo em sustentabilidade",
        "qual a situação da plataforma tecnológica",
        "como anda o nidum mundo",
        "o que rolou em operações",
        "estado atual da academia",
        "o que já convergiu sobre marketing",
        "me dá um panorama de comunidades vivas",
    ],
    "abertos": [
        "o que está em aberto na Nidum",
        "o que falta decidir",
        "quais os pontos em definição",
        "o que as convergências deixaram em aberto",
        "temas pendentes da rede",
    ],
}


def _people_set():
    d = FONTE_INDEX
    s = set()
    for g in (
        "ecossistemas_funcionais",
        "ecossistemas_produto",
        "ecossistemas_estruturais",
    ):
        for e in d[g]:
            if e["facilita"]:
                s.add(re.sub(r"\s*\(.*?\)", "", e["facilita"]).strip())
            s.update(re.sub(r"\s*\(.*?\)", "", p).strip() for p in e["protagonistas"])
    for o in d["orgaos"].values():
        s.update(o.get("membros", []))
    return s


def _find_person(q):
    ql = q.lower()
    cand = [p for p in _people_set() if p.lower() in ql]
    return max(cand, key=len) if cand else None


def _has_date(q):
    return bool(
        re.search(
            r"\b\d{1,2}[/ ]\d{1,2}|\bjaneiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro\b",
            q.lower(),
        )
    )


def _eco_in(q):
    ql = q.lower()
    for chaves, fe, ce in ECO_RESOLVE:
        if any(re.search(r"\b" + re.escape(k) + r"\b", ql) for k in chaves):
            return ce
    return None


def _handle(intent, q):
    T = Tools()
    if intent == "roster":
        return T.quadro_de_pessoas()
    if intent == "dedicacao":
        return T.dedicacao_intensiva()
    if intent == "ecossistema":
        return T.pessoas_do_ecossistema(q)
    if intent == "pessoa":
        n = _find_person(q)
        return T.papeis_de_uma_pessoa(n) if n else None
    if intent == "caminho_obra":
        return T.caminho_da_obra()
    if intent == "principios":
        return T.principios_economicos()
    if intent == "valores":
        return T.valores()
    if intent == "regua":
        return T.regua_de_valor()
    if intent == "estado_eco":
        eco = _eco_in(q)
        return T.estado_do_ecossistema(eco) if eco else None
    if intent == "abertos":
        return T.abertos_da_rede()
    return None


class Filter:
    class Valves(BaseModel):
        api_key: str = Field(
            default="", description="Chave da API de embeddings (a mesma do seu RAG)."
        )
        base_url: str = Field(
            default="https://api.openai.com/v1", description="Endpoint de embeddings."
        )
        model: str = Field(
            default="text-embedding-3-small", description="Modelo de embedding."
        )
        threshold: float = Field(
            default=0.50, description="Similaridade mínima (cosseno) para rotear."
        )
        enabled: bool = Field(default=True)

    def __init__(self):
        self.valves = self.Valves()
        self._intent_vecs = None

    def _embed(self, texts):
        r = requests.post(
            self.valves.base_url.rstrip("/") + "/embeddings",
            headers={
                "Authorization": "Bearer " + self.valves.api_key,
                "Content-Type": "application/json",
            },
            json={"model": self.valves.model, "input": texts},
            timeout=20,
        )
        r.raise_for_status()
        return [
            d["embedding"] for d in sorted(r.json()["data"], key=lambda x: x["index"])
        ]

    @staticmethod
    def _cos(a, b):
        s = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return s / (na * nb) if na and nb else 0.0

    def _ensure(self):
        if self._intent_vecs is None:
            flat, lab = [], []
            for name, exs in INTENTS.items():
                for e in exs:
                    flat.append(e)
                    lab.append(name)
            self._intent_vecs = list(zip(lab, self._embed(flat)))

    def _route(self, q):
        self._ensure()
        qv = self._embed([q])[0]
        sims = {}
        for name, v in self._intent_vecs:
            sims[name] = max(sims.get(name, 0.0), self._cos(qv, v))
        name = max(sims, key=sims.get)
        score = sims[name]
        # desambiguação por slot
        if _find_person(q):
            name = "pessoa"
        elif (
            _eco_in(q)
            and not _has_date(q)
            and name in ("roster", "estado_eco", "ecossistema")
        ):
            # pergunta sobre um ecossistema SEM data -> estado vigente (camada viva), salvo se pediu só o time
            if re.search(
                r"\bquem\b|time|equipe|pessoas|protagonistas|facilita", q.lower()
            ):
                name = "ecossistema"
            else:
                name = "estado_eco"
        return (name, score) if score >= self.valves.threshold else (None, score)

    def inlet(self, body: dict, __user__: dict = None) -> dict:
        if not self.valves.enabled or not self.valves.api_key:
            return body
        try:
            msgs = body.get("messages", [])
            users = [m for m in msgs if m.get("role") == "user"]
            if not users:
                return body
            q = users[-1].get("content", "")
            if isinstance(q, list):
                q = " ".join(str(x.get("text", "")) for x in q if isinstance(x, dict))
            if not q.strip():
                return body
            intent, score = self._route(q)
            if not intent:
                return body
            ans = _handle(intent, q)
            if not ans:
                return body
            inject = {
                "role": "system",
                "content": f"RESPOSTA OFICIAL DO ENGINE (intenção '{intent}', confiança {score:.2f}). "
                f"Entregue este conteúdo ao coautor começando pela etiqueta de certeza que já vem nele, "
                f"organizado e completo, sem resumir e sem inventar nada além:\n\n{ans}",
            }
            body["messages"] = [inject] + msgs
        except Exception:
            return body
        return body
