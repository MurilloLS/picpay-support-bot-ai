"""
PicPay Negócios — Bot de Suporte para Lojistas (versão elaborada)
=================================================================
"""

import os
import json
import time
import textwrap
from datetime import datetime
from typing import Iterator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.padding import Padding

from google import genai
from google.genai import types

# ── Configuração ───────────────────────────────────────────────────────────────
API_KEY     = os.environ.get("GEMINI_API_KEY", "SUA_CHAVE_AQUI")
MODEL       = "gemini-2.5-flash"
MAX_Q       = 3
MAX_RETRIES = 3
MAX_INPUT   = 400   # caracteres máximos por pergunta

console = Console()

# ── Knowledge Base e System Instruction ───────────────────────────────────────
SYSTEM_INSTRUCTION = """
Você é a Pi, assistente virtual de suporte do Portal PicPay Negócios para Lojistas.

## Personalidade
- Tom moderno, descontraído e objetivo — no estilo da marca PicPay
- Linguagem clara, sem juridiquês ou termos bancários complicados
- NUNCA inventa procedimentos — responde SOMENTE com base no conhecimento abaixo
- Se a pergunta estiver fora do escopo do Portal PicPay Negócios, informe educadamente
- Respostas sempre em português brasileiro

## Tarefa
- Responder EXATAMENTE 3 perguntas nesta sessão
- Na 3ª resposta: após responder normalmente, adicionar a seção
  "📋 RESUMO DO ATENDIMENTO" com um parágrafo coeso resumindo as três
  trocas desta conversa, e encerrar com uma despedida cordial

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KNOWLEDGE BASE — PICPAY NEGÓCIOS (PORTAL INTERNO PARA LOJISTAS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Acesso ao portal
- URL: https://lojista.picpay.com
- Login com e-mail e senha cadastrados no credenciamento
- App: "PicPay Negócios" (iOS e Android)
- Perda de acesso: "Esqueci a senha" na tela de login ou chat no portal

### Taxas de transação (MDR)
- PicPay Carteira (saldo PicPay): 0,99%
- Crédito à vista: 2,99%  |  Crédito 2x–6x: 3,49%  |  Crédito 7x–12x: 3,99%
- Débito: 1,49%           |  Pix: 0,99%
⚠️ Volume mensal > R$ 50.000: solicitar renegociação em "Meu Plano" > "Solicitar Revisão de Taxa" — análise em 5 dias úteis

### Prazo de recebimento (liquidação)
- PicPay Carteira, Pix, Débito: D+1
- Crédito à vista: D+30 (ou D+2 com antecipação automática)
- Crédito parcelado: cada parcela em D+30 da data da transação
Ativar antecipação: "Financeiro" > "Antecipação" > toggle "Antecipação Automática"
Taxa: 1,80% ao mês. Confirmação em até 1h útil.

### Contestação de chargeback
Chargeback = portador contesta compra junto à operadora.
Passo a passo:
  1. "Financeiro" > "Chargebacks" > clique em "Aguardando Documentação"
  2. Anexe: nota fiscal, comprovante de entrega, print do pedido
  3. "Enviar Contestação" — prazo: 10 dias corridos após notificação
  4. Resultado: até 30 dias úteis por e-mail
⚠️ Taxa de chargeback > 1% das transações mensais → monitoramento automático

### Bloqueio e limite
Causas: chargeback > 1%, suspeita de fraude, documentação vencida, descumprimento dos termos
Regularizar: "Minha Conta" > "Status do Cadastro" → verificar pendências
Contestar bloqueio: "Suporte" > "Abrir Chamado" > "Bloqueio de Conta" — análise em 3 dias úteis

### Saque e transferência
- Para conta PJ do titular: grátis, D+1
- Para outras contas: R$ 2,50 por saque, D+1
- Limite diário: R$ 20.000
- Ampliar limite: "Financeiro" > "Limites" > "Solicitar Aumento" + extrato 3 meses

### Relatórios e comprovantes
- "Relatórios" > período + formato (PDF/CSV) > "Gerar Relatório"
- Tipos: vendas, chargebacks, antecipações, repasses
- Comprovante avulso: clique na transação > "Baixar Comprovante"
- NF-e: NÃO emitida pelo PicPay — emitir pelo próprio sistema fiscal

### Cancelamento de transação
- Até 24h após captura: "Vendas" > transação > "Cancelar Transação" + motivo
- Após 24h: "Suporte" > "Estorno Manual"
- Estorno ao comprador: até 7 dias úteis

### PicPay Negócios Plus (volume > R$ 10.000/mês)
- Pix 0,75% | Antecipação 1,50% a.m. | Suporte prioritário | Gerente dedicado
- Aderir: "Meu Plano" > "Conhecer PicPay Negócios Plus"

### Suporte direto
- Chat portal/app: 24/7
- Telefone: 4004-5555 (capitais) | 0800 722 5555 — seg–sex 8h–20h, sáb 9h–15h
- E-mail financeiro: disputas.lojista@picpay.com
"""

class PicPayBot:
    def __init__(self):
        self.client   = genai.Client(api_key=API_KEY)
        self.history: list[types.Content] = []
        self.log: list[dict] = []         
        self.q_count  = 0
        self.started_at = datetime.now()

    # ── Validação de entrada ───────────────────────────────────────────────────
    @staticmethod
    def validate(text: str) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, "Digite sua pergunta antes de enviar."
        if len(text) > MAX_INPUT:
            return False, f"Pergunta muito longa ({len(text)} chars). Máximo: {MAX_INPUT}."
        return True, text

    # ── Prepara mensagem──────────────────────────────────────────────────────────
    def _prepare_message(self, user_text: str) -> str:
        if self.q_count + 1 >= MAX_Q:
            return (
                user_text
                + "\n\n[INSTRUÇÃO INTERNA — NÃO EXIBIR AO USUÁRIO: "
                "Esta é a 3ª e última pergunta. Após responder, adicione a seção "
                "'📋 RESUMO DO ATENDIMENTO' resumindo as três trocas desta sessão "
                "em um parágrafo coeso. Encerre com despedida cordial.]"
            )
        return user_text

    # ── Chamada à API com streaming e retry ───────────────────────────────────
    def _stream_response(self, prepared_text: str) -> Iterator[str]:
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=prepared_text)])
        )

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                stream = self.client.models.generate_content_stream(
                    model=MODEL,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                    ),
                    contents=self.history,
                )
                full_text = ""
                for chunk in stream:
                    piece = chunk.text or ""
                    full_text += piece
                    yield piece

                # Salva no histórico e no log SOMENTE após sucesso completo
                self.history.append(
                    types.Content(role="model", parts=[types.Part(text=full_text)])
                )
                return

            except Exception as exc:
                if attempt < MAX_RETRIES:
                    console.print(
                        f"  [yellow]⚠ Tentativa {attempt} falhou ({exc}). "
                        f"Aguardando {attempt * 2}s...[/yellow]"
                    )
                    time.sleep(attempt * 2)
                else:
                    # Remove última mensagem do usuário que não gerou resposta
                    self.history.pop()
                    raise RuntimeError(
                        f"API indisponível após {MAX_RETRIES} tentativas: {exc}"
                    ) from exc

    # ── Pergunta completa ───────────────
    def ask(self, user_input: str) -> bool:
        """
        Processa uma pergunta.
        Retorna True se é a última pergunta (sessão encerrada).
        """
        ok, user_input = self.validate(user_input)
        if not ok:
            console.print(f"  [red]{user_input}[/red]\n")
            return False

        self.q_count += 1
        is_last = self.q_count >= MAX_Q
        prepared = self._prepare_message(user_input)

        # ── Renderiza pergunta ─────────────────────────────────────────────────
        q_label = Text(f"  [{self.q_count}/{MAX_Q}] Você", style="bold green")
        console.print()
        console.print(q_label)
        console.print(Panel(user_input, border_style="green", padding=(0, 2)))

        # ── Streaming da resposta ──────────────────────────────────────────────
        console.print()
        console.print(Text("  Pi", style="bold magenta"))
        response_text = ""

        with Live(console=console, refresh_per_second=20) as live:
            buffer = ""
            for token in self._stream_response(prepared):
                buffer += token
                response_text = buffer
                live.update(
                    Panel(buffer, border_style="magenta", padding=(0, 2))
                )

        # ── Loga a troca ───────────────────────────────────────────────────────
        self.log.append({
            "q": self.q_count,
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "bot": response_text,
        })

        return is_last

    # ── Exporta sessão para arquivo de texto ──────────────────────────────────
    def export_session(self) -> str:
        now  = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"picpay_sessao_{now}.txt"

        lines = [
            "=" * 62,
            "  PicPay Negócios — Transcrição de Atendimento",
            f"  Início: {self.started_at.strftime('%d/%m/%Y %H:%M:%S')}",
            f"  Fim:    {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "=" * 62,
            "",
        ]
        for entry in self.log:
            lines += [
                f"[{entry['q']}/{MAX_Q}] Você ({entry['timestamp']}):",
                textwrap.fill(entry["user"], width=60, initial_indent="  "),
                "",
                "Pi:",
                textwrap.fill(entry["bot"], width=60, initial_indent="  "),
                "",
                "-" * 62,
                "",
            ]

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return path

    # ── Resumo da sessão em tabela ─────────────────────────────────────────────
    def print_session_table(self):
        table = Table(
            title="Resumo da sessão",
            show_header=True,
            header_style="bold magenta",
            border_style="magenta",
        )
        table.add_column("#",         width=3,  justify="center")
        table.add_column("Pergunta",  width=35)
        table.add_column("Horário",   width=10, justify="center")

        for entry in self.log:
            short = (entry["user"][:32] + "…") if len(entry["user"]) > 32 else entry["user"]
            ts    = entry["timestamp"][11:16]
            table.add_row(str(entry["q"]), short, ts)

        console.print(Padding(table, (1, 2)))


# ── Tela de boas-vindas ────────────────────────────────────────────────────────
def print_welcome():
    console.print()
    console.print(
        Panel(
            "[bold green]💚  PicPay Negócios  |  Suporte ao Lojista[/bold green]\n\n"
            "Olá! Sou a [bold magenta]Pi[/bold magenta], assistente do Portal PicPay.\n"
            f"Esta sessão aceita [bold]{MAX_Q} perguntas[/bold] sobre o portal interno.\n\n"
            "[dim]Tópicos disponíveis: taxas MDR, chargebacks, antecipação,\n"
            "bloqueios, saques, cancelamentos, relatórios e muito mais.[/dim]",
            border_style="green",
            padding=(1, 4),
        )
    )

    # Tabela de sugestões
    sug = Table(show_header=False, box=None, padding=(0, 2))
    sug.add_column(style="dim")
    sug.add_column(style="italic")
    sug.add_row("💡", "Como cancelo um pedido já aceito?")
    sug.add_row("💡", "Recebi um chargeback — o que faço?")
    sug.add_row("💡", "Como ativo a antecipação automática?")
    console.print(Padding(sug, (0, 2)))
    console.print()


# ── Tela de encerramento ───────────────────────────────────────────────────────
def print_farewell(bot: PicPayBot):
    console.print()
    console.print(Rule(style="magenta"))
    bot.print_session_table()

    path = bot.export_session()
    console.print(
        Panel(
            f"[green]✔[/green] Transcrição salva em [bold]{path}[/bold]\n\n"
            "[dim]Boas vendas! 💚[/dim]",
            border_style="green",
            padding=(0, 2),
        )
    )
    console.print()


# ── Loop principal ─────────────────────────────────────────────────────────────
def main():
    print_welcome()
    bot = PicPayBot()

    while bot.q_count < MAX_Q:
        remaining = MAX_Q - bot.q_count
        prompt_label = (
            f"[green]Pergunta {bot.q_count + 1}/{MAX_Q}[/green]"
            f" [dim]({remaining} restante{'s' if remaining != 1 else ''})[/dim] › "
        )
        try:
            user_input = console.input(prompt_label)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Atendimento interrompido.[/dim]")
            break

        try:
            session_ended = bot.ask(user_input)
        except RuntimeError as err:
            console.print(f"\n[red]Erro: {err}[/red]\n")
            continue

        if session_ended:
            break

    print_farewell(bot)


if __name__ == "__main__":
    main()
