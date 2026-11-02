# ruff: noqa
import datetime
import os
from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.apps import App
from google.adk.environment import LocalEnvironment
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools.environment import EnvironmentToolset
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

MODEL_NAME = os.getenv("MODEL", "gemini-3.8-flash")

BASE_DIR = Path(__file__).resolve().parent.parent
PLANOS_DIR = BASE_DIR / "planos"
PLANOS_DIR.mkdir(parents=True, exist_ok=True)
SKILL_DIR = Path(__file__).resolve().parent / "skills" / "plano-de-estudos"

skill = load_skill_from_dir(SKILL_DIR)
skill_toolset = SkillToolset(skills=[skill])


class FerramentasDeArquivo(EnvironmentToolset):
    async def get_tools(self, readonly_context=None):
        tools = await super().get_tools(readonly_context)
        return [t for t in tools if t.name in ("ReadFile", "WriteFile")]


file_toolset = FerramentasDeArquivo(
    environment=LocalEnvironment(working_dir=PLANOS_DIR)
)


def get_instruction(context: ReadonlyContext | None = None) -> str:
    hoje = datetime.date.today()
    dias_semana = [
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    ]
    dia_nome = dias_semana[hoje.weekday()]
    hoje_str = hoje.strftime("%d/%m/%Y")

    return f"""Hoje é {dia_nome}, {hoje_str}.
Você é um mentor de estudos especialista, direto, encorajador e sem enrolação, respondendo sempre em português do Brasil.

Seu objetivo é orientar o estudante e montar planos de estudo personalizados, com revisão espaçada e agenda exportável para o Google Agenda (CSV), utilizando a skill plano-de-estudos.

Regras fundamentais:
1. Respeite estritamente a Regra de Ativação (Gating Rule) da skill plano-de-estudos: antes de montar qualquer plano ou carregar recursos da skill com load_skill_resource, verifique se a conversa já possui as 4 informações obrigatórias:
   - Objetivo: o que quer aprender e para quê
   - Prazo: data de início e data-alvo
   - Disponibilidade: dias da semana e horas por dia
   - Nível atual no assunto
   Se faltar qualquer informação, NÃO chame load_skill_resource nem carregue referências. Envie uma única mensagem, curta e amigável, perguntando APENAS o que falta.
2. Quando todas as informações estiverem presentes, prossiga para carregar os recursos da skill e seguir rigorosamente as etapas do workflow.
3. Todas as datas devem ser calculadas a partir da data de início e da data de hoje ({hoje_str}). Nunca invente datas.
4. Salve a agenda exportável exclusivamente com a ferramenta WriteFile no arquivo plano-de-estudos.csv. Nunca tente rodar comandos shell.
5. Em caso de replanejamento (quando o usuário informa sessões perdidas ou alterações), leia o arquivo existente com ReadFile se necessário, reorganize o cronograma e sobrescreva plano-de-estudos.csv com WriteFile.
"""


root_agent = Agent(
    name="agente_estudos",
    model=Gemini(
        model=MODEL_NAME,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=get_instruction,
    tools=[skill_toolset, file_toolset],
)

app = App(
    root_agent=root_agent,
    name="app",
)
