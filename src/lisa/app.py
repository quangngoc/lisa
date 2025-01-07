import ast
import os
import locale
import sys
from openai import AsyncOpenAI
from lisa.scheduler import TimeSlotFetcher
from lisa.recognizer import recognize_date_time
import chainlit as cl

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


cl.instrument_openai()

api_key = os.environ.get("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)
MAX_ITER = 5


async def get_available_time_slots(date_string: str) -> str:
    date = await recognize_date_time(date_string)
    if not date:
        raise Exception(f"Can not recognize {date_string}")
    fetcher = TimeSlotFetcher()
    slots = await fetcher.fetch(date)
    if sys.platform.startswith("win"):
        date_str = slots.date.strftime("%A %#d %B")
    else:
        date_str = slots.date.strftime("%A %-d %B")
    return f"Les créneaux disponibles du {date_str}: {str(slots.slots)}"


system_prompt = """Vous êtes LISA - un assistant vocal conçu pour planifier des rendez-vous pour les utilisateurs.
Votre objectif principal est d'aider les utilisateurs à trouver des horaires de rendez-vous adaptés en fonction des disponibilités fournies. Voici vos instructions :

1. Demandez à l'utilisateur sa date et son heure préférées pour un rendez-vous, et soyez attentif à son langage naturel.
2. Comprenez et interprétez le langage naturel concernant les dates et les heures, en tenant compte des ambiguïtés possibles.
3. Appelez les fonctions backend pour vérifier les créneaux horaires disponibles. Si aucun créneau n'est retourné (liste vide ou valeur nulle), reformulez poliment une question ou demandez des précisions à l'utilisateur pour mieux comprendre ses besoins. Par exemple, vous pouvez dire :
- "Je ne vois pas de disponibilité pour cette date. Souhaiteriez-vous essayer un autre jour ou une autre plage horaire?"
- "Je n'ai pas compris votre demande. Pourriez-vous préciser votre préférence de date ou d'heure?"
4. Lorsque des créneaux sont disponibles, proposez un maximum de deux options à l'utilisateur de manière naturelle et intégrée dans la conversation, sans énumération ou listes numérotées. Alternez vos formulations pour éviter la monotonie, par exemple :
- "Je peux vous proposer ces horaires: [option 1] ou [option 2]. Lequel préférez-vous?"
- "Ces créneaux sont disponibles: [option 1] et [option 2]. Est-ce qu'un de ces horaires vous convient?"
5. Formulez vos réponses comme dans une conversation orale. Utilisez des phrases fluides et naturelles, adaptées à une communication vocale, et évitez les sauts de ligne excessifs ou les énumérations rigides.
6. Adaptez vos réponses en fonction des interactions avec l'utilisateur. Ne proposez pas les créneaux déjà refusés, afin de maintenir une expérience fluide et agréable.
7. Confirmez toujours le rendez-vous de manière claire, et assurez-vous que l'utilisateur est satisfait de l'horaire réservé.
8. Soyez poli, concis et clair dans toutes vos communications. Utilisez des phrases courtes et engageantes pour maintenir l'intérêt de l'utilisateur.
9. Répondez de manière appropriée à toute préoccupation ou question exprimée par l'utilisateur. Si nécessaire, reformulez vos propositions pour mieux correspondre à ses attentes.
10. Introduisez des variations dans vos réponses pour éviter les répétitions et rendez la conversation dynamique et engageante."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_available_time_slots",
            "description": "Retrieve available date and time slots for appointment booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_string": {
                        "type": "string",
                        "description": "The specific or relative date (e.g., tomorrow, next week, a specific date).",
                    }
                },
                "required": ["date_string"],
            },
        },
    }
]


@cl.on_chat_start
async def start_chat():
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": system_prompt}],
    )
    message_history = cl.user_session.get("message_history")
    welcome_msg = "Bonjour! Je suis LISA, votre assistante vocale. Quand souhaitez-vous prendre un rendez-vous ?"
    message_history.append({"role": "assistant", "content": welcome_msg})
    assistant_message = cl.Message(content=welcome_msg, author="LISA")
    await assistant_message.send()


@cl.step(type="tool")
async def call_tool(tool_call_id, name, arguments, message_history):
    arguments = ast.literal_eval(arguments)
    current_step = cl.context.current_step
    current_step.name = name
    current_step.input = arguments
    function_response = await get_available_time_slots(date_string=arguments.get("date_string"))
    current_step.output = function_response
    current_step.language = "json"
    message_history.append(
        {
            "role": "tool",
            "name": name,
            "content": function_response,
            "tool_call_id": tool_call_id,
        }
    )


async def call_gpt4(message_history):
    settings = {
        "model": os.environ["MODEL_NAME"],
        "tools": tools,
        "tool_choice": "auto",
    }
    stream = await client.chat.completions.create(messages=message_history, stream=True, **settings)
    final_answer = cl.Message(content="", author="LISA")

    tool_calls = []
    full_delta_content = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices and chunk.choices[0].delta is not None else None
        if delta and delta.content:
            full_delta_content += delta.content
            if not final_answer.content:
                await final_answer.send()
            await final_answer.stream_token(delta.content)
        elif delta and delta.tool_calls:
            tc_chunk_list = delta.tool_calls
            for tc_chunk in tc_chunk_list:
                if len(tool_calls) <= tc_chunk.index:
                    tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                tc = tool_calls[tc_chunk.index]
                if tc_chunk.id:
                    tc["id"] += tc_chunk.id
                if tc_chunk.function.name:
                    tc["function"]["name"] += tc_chunk.function.name
                if tc_chunk.function.arguments:
                    tc["function"]["arguments"] += tc_chunk.function.arguments

    if tool_calls:
        message_history.append({"role": "assistant", "tool_calls": tool_calls})
        for tool_call in tool_calls:
            await call_tool(
                tool_call["id"],
                tool_call["function"]["name"],
                tool_call["function"]["arguments"],
                message_history,
            )

    if final_answer.content:
        await final_answer.update()
    return [tool_call_id for tool_call_id in tool_calls]


@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})
    cur_iter = 0
    while cur_iter < MAX_ITER:
        tool_call_ids = await call_gpt4(message_history)
        if not tool_call_ids:
            break
        cur_iter += 1


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit(__file__)
