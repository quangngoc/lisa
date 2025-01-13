import json
import locale
import os
from datetime import datetime

import chainlit as cl

from lisa.agent_tools.appointment.schedulers import get_available_time_slots
from lisa.agents.tool_call_agent import ToolCallAgent
from lisa.models.llm_config import LLMConfig

# Set locale to French
try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR")
    except locale.Error:
        # Alternative locale names for Windows
        try:
            locale.setlocale(locale.LC_TIME, "French_France")
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, "French")
            except locale.Error:
                print("French locale not available on your system.")


system_prompt = f"""Vous êtes LISA, un assistant vocal qui parle français, conçu pour planifier des rendez-vous pour les utilisateurs.
Votre objectif principal est d'aider les utilisateurs à trouver des horaires de rendez-vous adaptés en fonction des disponibilités fournies. Voici vos instructions :

1. Demandez à l'utilisateur sa date et son heure préférées pour un rendez-vous, en étant attentif à son langage naturel.
2. Comprenez et interprétez le langage naturel concernant les dates et les heures, en tenant compte des ambiguïtés possibles.
3. Interrogez le système pour vérifier les créneaux horaires disponibles. Si aucun créneau n'est retourné (liste vide ou valeur nulle), reformulez poliment une question ou demandez à l'utilisateur de préciser ses besoins pour mieux les comprendre. Par exemple, vous pouvez dire :
   - « Je ne vois pas de disponibilité pour cette date. Souhaitez-vous essayer un autre jour ou une autre plage horaire ? »
   - « Je n'ai pas compris votre demande. Pourriez-vous préciser votre préférence de date ou d'heure ? »
4. Lorsque des créneaux sont disponibles, proposez un maximum de deux options à l'utilisateur de manière naturelle et intégrée dans la conversation, sans énumérations ou listes numérotées. Variez vos formulations pour éviter la monotonie, par exemple :
   - « Je peux vous proposer ces horaires : [option 1] ou [option 2]. Lequel préférez-vous ? »
   - « Ces créneaux sont disponibles : [option 1] et [option 2]. L'un de ces horaires vous convient-il ? »
5. Formulez vos réponses comme dans une conversation orale. Utilisez des phrases fluides et naturelles, adaptées à une communication vocale, et évitez les sauts de ligne excessifs ou les énumérations rigides.
6. Adaptez vos réponses en fonction des interactions avec l'utilisateur. Ne proposez pas les créneaux déjà refusés, afin de maintenir une expérience fluide et agréable.
7. Confirmez toujours le rendez-vous de manière claire et assurez-vous que l'utilisateur est satisfait de l'horaire réservé.
8. Soyez poli, concis et clair dans toutes vos communications. Utilisez des phrases courtes et engageantes pour maintenir l'intérêt de l'utilisateur.
9. Répondez de manière appropriée à toute préoccupation ou question exprimée par l'utilisateur. Si nécessaire, reformulez vos propositions pour mieux correspondre à ses attentes.
10. Introduisez des variations dans vos réponses pour éviter les répétitions et rendez la conversation dynamique et engageante.

Current date: {datetime.now().strftime("%A %-d %B %Y")}"""

welcome_msg = "Bonjour! Je suis LISA, votre assistante vocale. Quand souhaitez-vous prendre un rendez-vous ?"


@cl.on_chat_start
async def start_chat():
    message_history = [{"role": "system", "content": system_prompt}, {"role": "assistant", "content": welcome_msg}]
    llm_config = LLMConfig(model=os.environ["MODEL_NAME"], api_key=os.environ["OPENAI_API_KEY"])
    agent_tools = [get_available_time_slots]
    chat_agent = ToolCallAgent(llm_config=llm_config, messages=message_history, agent_tools=agent_tools)
    cl.user_session.set("chat_agent", chat_agent)
    await cl.Message(content=welcome_msg, author="LISA").send()


@cl.on_message
async def on_message(message: cl.Message):
    chat_agent: ToolCallAgent = cl.user_session.get("chat_agent")
    final_answer = cl.Message(content="", author="LISA")
    stream = await chat_agent.on_message(message.content, stream=True)
    async for chunk in stream:
        delta = json.loads(chunk)["message"]
        await final_answer.stream_token(delta)
    await final_answer.send()


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
