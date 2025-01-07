import ast
import os
import locale
import sys
from openai import AsyncOpenAI
from lisa.scheduler import TimeSlotFetcher
from lisa.recognizer import recognize_date_time
import asyncio
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
    # Check the platform and format accordingly
    if sys.platform.startswith("win"):
        date_str = slots.date.strftime("%A %#d %B")
    else:
        date_str = slots.date.strftime("%A %-d %B")
    return f"{date_str}: {str(slots.slots)}"


system_prompt = """Vous êtes LISA - un assistant vocal conçu pour planifier des rendez-vous pour les utilisateurs.
Votre objectif principal est d'aider les utilisateurs à trouver des horaires de rendez-vous adaptés en fonction des disponibilités fournies par un système backend. Vous devez :

1. Demander sa date et son heure préférées pour un rendez-vous.
2. Comprendre et interpréter le langage naturel concernant les dates et les heures.
3. Appeler les fonctions appropriées pour vérifier les créneaux horaires disponibles lorsque cela est nécessaire.
4. Ne jamais énumérer tous les créneaux horaires disponibles. Proposez un maximum de deux options à l'utilisateur de manière naturelle et intégrée dans la conversation, sans utiliser de numérotation ou de listes. Variez la manière de proposer ces options pour éviter les répétitions. Par exemple, au lieu de toujours dire "Lequel vous conviendrait le mieux ?", alternez avec des formulations comme "Y a-t-il un moment qui vous convient parmi ceux-ci ?" ou "Quelle heure aimeriez-vous choisir ?".
5. Formuler vos réponses comme dans une véritable conversation orale, en évitant les structures qui ne sont pas adaptées à la parole, telles que les numéros de liste ou les sauts de ligne excessifs. Assurez-vous que vos phrases sont fluides et naturelles lorsqu'elles sont prononcées à voix haute.
6. Être attentif aux réponses de l'utilisateur et éviter de répéter les informations déjà fournies. Souvenez-vous des horaires déjà refusés pour ne pas les proposer à nouveau, afin de maintenir une conversation fluide et agréable.
7. Confirmer les rendez-vous clairement et s'assurer que l'utilisateur est satisfait de l'heure réservée.
8. Être poli, concis, éviter les phrases trop longues, et garantir la clarté dans toutes vos communications.
9. Reconnaître toute préoccupation ou question de l'utilisateur et y répondre de manière appropriée.
10. Introduire des variations dans vos réponses pour éviter la monotonie, en faisant attention à reformuler les propos précédents lorsque c'est possible. Utilisez un langage naturel et engageant pour maintenir l'intérêt de l'utilisateur tout au long de la conversation."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_available_time_slots",
            "description": "Récupérer les horaires de rendez-vous disponibles pour la réservation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_string": {
                        "type": "string",
                        "description": "La date spécifique ou relative (demain, semaine prochaine, ...)",
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

    function_response = await get_available_time_slots(
        date_string=arguments.get("date_string"),
    )

    current_step.output = function_response
    current_step.language = "json"
    message_history.append(
        {
            "role": "function",
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
        "temperature": 0,
    }

    stream = await client.chat.completions.create(messages=message_history, stream=True, **settings)
    final_answer = cl.Message(content="", author="LISA")

    tool_calls = {}
    tool_call_id = None
    async for part in stream:
        new_delta = part.choices[0].delta
        tool_call = new_delta.tool_calls and new_delta.tool_calls[0]
        function = tool_call and tool_call.function
        if tool_call and tool_call.id:
            tool_call_id = tool_call.id
            tool_calls[tool_call_id] = {"name": "", "arguments": ""}

        if function:
            if function.name:
                tool_calls[tool_call_id]["name"] = function.name
            else:
                tool_calls[tool_call_id]["arguments"] += function.arguments

        if new_delta.content:
            if not final_answer.content:
                await final_answer.send()
            await final_answer.stream_token(new_delta.content)

    # Process all tool calls in parallel
    if tool_calls:
        await asyncio.gather(
            *(
                call_tool(
                    tool_call_id,
                    tool_calls[tool_call_id]["name"],
                    tool_calls[tool_call_id]["arguments"],
                    message_history,
                )
                for tool_call_id in tool_calls
            )
        )

    if final_answer.content:
        await final_answer.update()

    # Return the list of tool_call IDs
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
