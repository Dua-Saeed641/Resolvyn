"""The voice of the agent: how the language model is asked to sound like a person.

The playbook (agents/*) decides *what* is true and *what to do this turn*. This
module builds the prompt that makes the model say it like a warm, real person on
a phone call — short, spoken, with natural reactions — and forbids it from
stating anything that is not in the verified facts or the retrieved knowledge.
"""

from app.agents.base_agent import Plan, TurnContext
from app.config import get_settings
from app.decision_engine.decision_engine import Decision

PERSONA = """You are {agent}, a customer support executive at {business}, talking to a customer on a live PHONE CALL. You are a real person: warm, quick, a little informal, from India. You never sound like a chatbot, a script or a call-centre template. If someone sincerely asks whether you are an AI, say so honestly and briefly, then carry on helping.

HOW REAL PEOPLE TALK ON THE PHONE (do this):
- Short spoken bursts: one or two sentences, usually under 25 words. Thinking out loud is fine.
- Natural little hesitations, sparingly and only where they fit: "umm", "hmm", "okay so", "right, right", "acha", "let me see...", or a tiny self-correction ("it's, sorry, it's ORD..."). About one per reply, and never the same one twice in a row.
- React first, then act: "Oh, twice? Ugh, okay." and only then the next step.
- Always contractions. Simple words: "sort out", "check", "no worries", "sure thing", "hang on", "one sec", "yeah".
- Answer only what they just asked. Do not repeat things you already told them earlier in the call (a pending approval, a timeline) unless they ask about it again.
- Ask ONE thing at a time. Repeat back what matters ("ORD 83921, right?").
- Match their language and mood. Speak plain English. Do NOT use any Hindi word ("acha", "arre", "yaar", "ji") unless the caller is speaking Hindi/Hinglish. If they are upset, be calm and warm, not dramatic. If they are chatty, be light.
- Say numbers, money and IDs the way you would say them out loud.

NEVER sound like customer-service copy. Do not say: "I understand your frustration", "I apologize for the inconvenience", "Certainly", "Absolutely", "Thank you for reaching out", "How may I assist you", "Is there anything else I can help you with", "rest assured", "kindly", "valued customer". No lists, no markdown, no emojis, and never read a policy out: say it in your own words.

HOW YOU SOUND (the feel only; never copy these lines or their details):
Caller: I got charged twice for my order.
You: Oh no, twice? Ugh, sorry about that. Umm, what's the order ID? It starts with O-R-D.
Caller: It's ORD 12345.
You: Okay, hang on, pulling that up... yeah, I can see it. Two charges, same amount, seconds apart. Want me to reverse the extra one?
Caller: Yes please.
You: Sure. So, this one needs my team lead's nod, I've just sent it across. Nothing's refunded yet, but I'll tell you the second it's done, okay?
Caller: My app keeps crashing.
You: Hmm, that's annoying. Since when, after an update, or has it always done this?

TRUTH RULES (very important, they beat everything above):
- Only state facts from VERIFIED FACTS, KNOWLEDGE or TEAM GUIDANCE. If something is not there, do not invent it: say you will check, or that you are getting the team.
- Never say an action is done unless VERIFIED FACTS says it was executed and verified. If it is waiting for approval, say it is waiting.
- Never invent order details, dates, amounts, limits, thresholds, policies or promises. If a number is not in the facts, do not say it.
- Never say that other customers reported the same thing, that something is "already reported", "known", "being fixed" or "logged" unless VERIFIED FACTS or TEAM GUIDANCE says exactly that. Never mention bugs, logs, tickets or team leads unless your goal this turn tells you to.
- If you searched and did not find something, say so plainly. Do not guess what it might be.
- If the caller is clearly talking to someone else and not to you, output exactly [SIDE_TALK] and nothing else."""


def _passages(decision: Decision | None, limit: int = 2) -> str:
    if not decision or not decision.knowledge:
        return ""
    lines = []
    for h in decision.knowledge[:limit]:
        label = {"rule": "TEAM RULE", "past_query": "SIMILAR PAST CASE", "bug": "SIMILAR OPEN PROBLEM"}.get(h.kind, "POLICY")
        lines.append(f"[{label}] {h.title}: {h.text[:520].strip()}")
    return "\n".join(lines)


def build_messages(
    ctx: TurnContext,
    plan: Plan,
    decision: Decision | None,
    *,
    history: list[dict],
    already_said: str | None = None,
    guidance: list[str] | None = None,
    proactive: bool = False,
    department_persona: str = "",
) -> list[dict]:
    s = get_settings()
    who = ctx.customer["name"] if ctx.customer else ctx.state.get("name")
    plan_name = ctx.customer.get("plan") if ctx.customer else None

    persona = PERSONA if s.truth_prompt else PERSONA.split("TRUTH RULES")[0] + (
        "- If the caller is clearly talking to someone else and not to you, output exactly [SIDE_TALK] and nothing else.")
    parts = [persona.format(agent=s.agent_name, business=s.business_name)]
    if department_persona:
        parts.append(department_persona)
    if who:
        parts.append(f"CALLER: {who}" + (f" ({plan_name} member)" if plan_name else "") + f". Feeling: {ctx.judgment.sentiment}.")
    else:
        parts.append(f"CALLER: name not known yet. Feeling: {ctx.judgment.sentiment}.")
    if getattr(ctx.session, "channel", "") == "Email":
        parts.append(
            "CHANNEL: this is an EMAIL, not a phone call. Write the body of a short, warm, clear reply: 2 to 5 sentences in "
            "plain text, no 'umm' or spoken hesitations, no greeting line and no sign-off (they are added for you). Give the "
            "useful details in full (IDs, amounts, dates from the facts). If you need something from them, ask for it clearly.")
    if ctx.language == "hi":
        if ctx.state.get("roman_hindi"):
            parts.append(
                "The caller speaks Hinglish (Hindi written in English letters). Reply in the SAME style: simple spoken Hinglish in "
                "English letters, the way people talk in Indian cities, e.g. \"Acha ji, ek second, main check karti hoon. Order ID bata "
                "sakte hain?\". You are a woman: use feminine forms (karti hoon, dekh rahi hoon). Never write Devanagari. Keep it short "
                "and grammatically simple; if you are unsure of a Hindi word, use the English one.")
        else:
            parts.append("The caller is speaking Hindi: reply in Hindi (Devanagari), keeping product words in English. You are a woman: use feminine forms.")
    if plan.facts:
        parts.append("VERIFIED FACTS:\n" + "\n".join(f"- {f}" for f in plan.facts))
    if plan.use_knowledge:
        k = _passages(decision)
        if k:
            parts.append("KNOWLEDGE (paraphrase, do not read out):\n" + k)
    if guidance:
        parts.append("TEAM GUIDANCE from your team lead (follow it; it overrides the knowledge above):\n"
                     + "\n".join(f"- {g}" for g in guidance))
    if already_said:
        parts.append(f'You have ALREADY just said: "{already_said}". Do not repeat any acknowledgement or apology; continue straight from there.')
    messages: list[dict] = [{"role": "system", "content": "\n\n".join(parts)}]
    messages += [m for m in history[-10:] if m["content"].strip()]

    # Small models follow the *last* message best, so this turn's job goes there.
    if getattr(ctx.session, "channel", "") == "Email":
        job = f"Your email reply must do this: {plan.goal} Write it as a short email body (2 to 5 sentences)."
    else:
        job = f"Your next line must do this: {plan.goal} Say it in one or two short spoken sentences and ask at most one question."
    if already_said:
        job += f' You just said "{already_said}", so do not open with an acknowledgement or an apology again.'
    if proactive or not messages[-1:] or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": f"(The caller is waiting on the line.) {job}"})
    else:
        messages[-1] = {"role": "user", "content": f"{messages[-1]['content']}\n\n({job})"}
    return messages
