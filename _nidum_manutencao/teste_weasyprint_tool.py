"""
title: Teste WeasyPrint
author: Nidum
version: 0.1.0
description: Ferramenta descartavel - testa se o WeasyPrint importa e renderiza um PDF na imagem VIVA do Open WebUI (imagem do Railway). Apagar depois do teste.
requirements: weasyprint
"""

# COLE ESTE CODIGO em Workspace -> Ferramentas -> Nova Ferramenta (id: teste_weasyprint).
# O Open WebUI instala o weasyprint (do header requirements) ao salvar.
# Depois: acople a um modelo e peca no chat para rodar a ferramenta "testar".
# So-ASCII (regra do projeto).


class Tools:
    def __init__(self):
        pass

    async def testar(self, __user__: dict = None) -> str:
        """Testa se o WeasyPrint funciona nesta imagem: importa e renderiza um PDF pequeno."""
        try:
            import weasyprint
        except Exception as e:
            return "FALHOU no import do weasyprint: %s: %s" % (type(e).__name__, str(e)[:400])
        try:
            html = (
                "<html><head><meta charset='utf-8'></head><body>"
                "<h1>Teste WeasyPrint</h1>"
                "<p>Acentuacao correta: atencao a juncao, ceramica, area.</p>"
                "</body></html>"
            )
            pdf = weasyprint.HTML(string=html).write_pdf()
        except Exception as e:
            return ("Importou, mas FALHOU ao renderizar (provavel falta de lib de "
                    "sistema pango/cairo/gdk-pixbuf): %s: %s" % (type(e).__name__, str(e)[:400]))
        versao = getattr(weasyprint, "__version__", "?")
        return "WeasyPrint OK. versao=%s | PDF de teste gerado com %d bytes. Pode seguir com a Rota A." % (versao, len(pdf))
