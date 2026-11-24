import os
import random
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

st.set_page_config(
    page_title="Escape the Island",
    page_icon="🏝️",
    layout="centered",
)
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(
            160deg,
            #b9e8ef 0%,
            #d8f0df 52%,
            #f6e5c4 100%
        );
        background-attachment: fixed;
    }

    .stApp,
    .stApp * {
        color: #000000 !important;
    }

    .stApp p,
    .stApp label,
    .stApp button,
    .stApp input,
    .stApp [data-testid="stCaptionContainer"] {
        font-size: 1.05rem !important;
    }

    div[data-testid="stButton"] > button {
        background-color: #ffffff !important;
        border: 1px solid #000000 !important;
    }

    div[data-testid="stButton"] > button:hover {
        background-color: #d9f2ff !important;
    }

    div[data-testid="stTextInput"] {
        max-width: 18rem;
    }

    div[data-testid="stTextInput"] input {
        height: 2.4rem;
        padding: 0.4rem 0.6rem;
        background-color: #d9f2ff !important;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🏝️ Escape the Island")


if "game_started" not in st.session_state:
    st.session_state.game_started = False

required_game_state = (
    "player_name",
    "health",
    "max_health",
    "inventory",
    "rooms",
    "room_number",
    "result_type",
    "result_message",
    "result_value",
    "action_complete",
    "failed_signals",
    "wreckage_stage",
)
if st.session_state.game_started and any(
    key not in st.session_state for key in required_game_state
):
    st.session_state.game_started = False


def start_game(name):
    # Initialize the player's state and begin a new island adventure.
    st.session_state.game_started = True
    st.session_state.player_name = name
    st.session_state.health = 5
    st.session_state.max_health = 5
    st.session_state.inventory = ["Torch"]
    st.session_state.rooms = [
        "wreckage",
        "shore",
        "cove",
        "jungle",
        "cliff",
        "camp",
        "rescue_point",
    ]
    st.session_state.room_number = 0
    st.session_state.result_type = ""
    st.session_state.result_message = ""
    st.session_state.result_value = ""
    st.session_state.action_complete = False
    st.session_state.failed_signals = 0
    st.session_state.wreckage_stage = 0


def restart_game():
    # Clear the session and restart the application.
    st.session_state.clear()
    st.rerun()


def get_current_room():
    # Return the name of the player's current location.
    return st.session_state.rooms[st.session_state.room_number]


def continue_game():
    # Clear the current result and move to the next location.
    st.session_state.result_type = ""
    st.session_state.result_message = ""
    st.session_state.result_value = ""
    st.session_state.action_complete = False
    if (
        st.session_state.room_number == 0
        and st.session_state.wreckage_stage == 1
    ):
        st.session_state.wreckage_stage = 2
        st.rerun()
    st.session_state.room_number += 1
    st.rerun()


def set_result(result_type, message, value=""):
    # Store an action result and rerun the app.
    st.session_state.result_type = result_type
    st.session_state.result_message = message
    st.session_state.result_value = value
    st.session_state.action_complete = True
    st.rerun()


def add_item(item):
    # Add an item to inventory if it is not already present.
    if item not in st.session_state.inventory:
        st.session_state.inventory.append(item)


def has_item(item):
    # Return whether an item is in the player's inventory.
    return item in st.session_state.inventory


def remove_item(item):
    # Remove an item from inventory if it is present.
    if item in st.session_state.inventory:
        st.session_state.inventory.remove(item)


def take_damage(amount):
    # Subtract damage without reducing health below zero.
    old_health = st.session_state.health
    st.session_state.health = max(0, old_health - amount)
    return old_health - st.session_state.health


def heal_player(amount):
    # Restore health without exceeding maximum health.
    old_health = st.session_state.health
    st.session_state.health = min(
        st.session_state.max_health,
        st.session_state.health + amount,
    )
    return st.session_state.health - old_health


def generate_story(room, action, outcome, fallback_message):
    # Generate an AI story or return the built-in fallback description.
    if client is None:
        return fallback_message

    inventory_text = ", ".join(st.session_state.inventory)
    prompt = f"""
You are the storyteller for a survival adventure game called Escape the Island.

Player: {st.session_state.player_name}
Location: {room}
Health: {st.session_state.health}/{st.session_state.max_health}
Inventory: {inventory_text}

Action:
{action}

Outcome:
{outcome}

Describe what happens in 30-50 words.
Use second person, present tense, and atmospheric survival language.
Stay in the current location; do not describe what happens next.
Do not invent characters, items, or events beyond the action and outcome.
Do not change the outcome, health, or inventory.
Keep the description clear and suitable for a general audience.
"""
    try:
        interaction = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt,
            generation_config={"thinking_level": "minimal"},
        )
        if interaction.output_text:
            return interaction.output_text
        return fallback_message
    except Exception as error:
        st.error(f"Gemini error: {error}")
        return fallback_message


def roll_dice():
    # Return a random value from one to six.
    return random.randint(1, 6)


def chance_encounter(
    button_text,
    room,
    action,
    success_number,
    success_outcome,
    success_fallback,
    failure_outcome,
    failure_fallback,
    damage,
    bonus_item="",
):
    # Run a dice-based action with optional equipment bonus.
    if st.button(button_text):
        roll = roll_dice()
        if bonus_item and has_item(bonus_item):
            roll += 2
        if roll >= success_number:
            story = generate_story(room, action, success_outcome, success_fallback)
            set_result("success", story)
        else:
            damage_taken = take_damage(damage)
            story = generate_story(room, action, failure_outcome, failure_fallback)
            set_result("damage", story, damage_taken)


def show_room(title, description):
    # Display the current location's title and description.
    st.header(title)
    st.write(description)


def show_player_info():
    # Display player name, health, inventory, and healing action.
    st.subheader(f"🧑 {st.session_state.player_name}")
    left, right = st.columns(2)
    with left:
        st.write(
            f"❤️ Health: {st.session_state.health}/"
            f"{st.session_state.max_health}"
        )
    with right:
        inventory = ", ".join(st.session_state.inventory)
        st.write(f"🎒 Inventory: {inventory}")

    if (
        st.session_state.health > 0
        and st.session_state.result_type not in ("lose", "win")
        and has_item("Healing Herb")
        and st.session_state.health < st.session_state.max_health
    ):
        if st.button("🌿 Use Healing Herb"):
            healed = heal_player(2)
            remove_item("Healing Herb")
            set_result(
                "heal",
                f"You use the Healing Herb and recover {healed} health.",
                healed,
            )

    st.caption(
        f"Location {st.session_state.room_number + 1}"
        f" of {len(st.session_state.rooms)}"
    )
    st.divider()


def show_result():
    # Display the outcome for the player's latest action.
    kind = st.session_state.result_type
    value = st.session_state.result_value

    if kind == "story":
        st.write(st.session_state.result_message)
        return
    if kind == "item":
        st.success(f"🎒 NEW ITEM: {value}")
    elif kind == "damage":
        st.error(f"💔 DAMAGE: You lose {value} health.")
    elif kind == "heal":
        st.success(f"💚 HEALED: You recover {value} health.")
    elif kind == "win":
        st.success("🏆 YOU WIN! Rescue has reached the island.")
        st.balloons()
    elif kind == "lose":
        st.error("💀 YOU LOSE! No rescue arrives.")
    elif kind == "success":
        st.success("✅ Success!")
    else:
        st.info("The journey continues...")

    st.write(st.session_state.result_message)


def show_continue_button(text="Continue"):
    # Show a game-over retry or continue to the next location.
    if st.session_state.health <= 0:
        if st.button("🔄 Play Again"):
            restart_game()
    elif st.button(text):
        continue_game()


if not st.session_state.game_started:
    st.write(
        "Your plane crashed on a remote island. You wake injured and alone. "
        "You walk to the wreckage, but find no other passengers. "
        "With rescue uncertain, you decide to search the crash site."
    )
    name = st.text_input("What is your name?")

    if st.button("Begin the Adventure"):
        if name.strip():
            start_game(name.strip())
            st.rerun()
        else:
            st.warning("Enter your name first.")

    st.stop()


show_player_info()
room = get_current_room()

if st.session_state.health <= 0:
    show_room("💀 YOU LOSE", "Your strength gives out. The island claims another survivor.")
    st.error("You did not escape the island.")
    if st.button("🔄 Try Again"):
        restart_game()
    st.stop()


if room == "wreckage":
    show_room(
        "✈️ The Crashed Plane",
        "The plane lies broken on the shore. There are no other passengers. "
        "Search around the wreckage before looking inside the plane.",
    )
    if not st.session_state.action_complete:
        if st.session_state.wreckage_stage == 0:
            if st.button("🔎 Search around the wreckage"):
                add_item("Rusty Machete")
                st.session_state.wreckage_stage = 1
                story = generate_story(
                    "The Crashed Plane",
                    "search around the wreckage",
                    "The player finds a Rusty Machete among the debris.",
                    "You search around the wreckage and find a Rusty Machete. "
                    "No passengers are anywhere in sight.",
                )
                set_result("item", story, "Rusty Machete")
        else:
            left, right = st.columns(2)
            with left:
                if st.button("🎒 Search inside the crashed plane"):
                    add_item("Signal Flare")
                    story = generate_story(
                        "The Crashed Plane",
                        "search inside the crashed plane after finding the machete",
                        "The player finds a Signal Flare inside the plane.",
                        "After finding the machete outside, you search inside "
                        "the plane and find a Signal Flare.",
                    )
                    set_result("item", story, "Signal Flare")
            with right:
                if st.button("➡️ Leave for the shore"):
                    story = generate_story(
                        "The Crashed Plane",
                        "leave the wreckage without searching inside the plane",
                        "The player leaves without finding a Signal Flare and continues toward the shore.",
                        "You leave the wreckage without searching inside and "
                        "continue toward the shore.",
                    )
                    set_result("story", story)
    else:
        if st.session_state.wreckage_stage == 1:
            show_result()
            show_continue_button("Continue")
        else:
            show_result()
            show_continue_button()


elif room == "shore":
    show_room("🌊 The Shore", "The tide carries debris across the sand.")
    if not st.session_state.action_complete:
        left, right = st.columns(2)
        with left:
            if st.button("🔎 Search the debris"):
                story = generate_story(
                    "The Shore",
                    "search the debris",
                    "The player searches the debris but finds nothing useful.",
                    "You search the washed-up debris but find nothing useful.",
                )
                set_result("story", story)
        with right:
            if st.button("➡️ Ignore it"):
                story = generate_story(
                    "The Shore",
                    "ignore the debris",
                    "The player leaves the debris and walks inland.",
                    "You leave the debris and follow the trail inland.",
                )
                set_result("story", story)
    else:
        show_result()
        show_continue_button()


elif room == "cove":
    show_room("🐚 The Hidden Cove", "A stranded supply crate rests beside the shore.")
    if not st.session_state.action_complete:
        left, right = st.columns(2)
        with left:
            if st.button("🔎 Search the supply crate"):
                story = generate_story(
                    "The Hidden Cove",
                    "search the stranded supply crate",
                    "The player searches the supply crate but finds nothing useful.",
                    "You search the supply crate but find nothing useful.",
                )
                set_result("story", story)
        with right:
            if st.button("🚪 Leave the cove"):
                story = generate_story(
                    "The Hidden Cove",
                    "leave the cove",
                    "The player leaves the cove undisturbed.",
                    "You leave the cove undisturbed.",
                )
                set_result("story", story)
    else:
        show_result()
        show_continue_button()


elif room == "jungle":
    show_room("🌿 The Dense Jungle", "A narrow trail leads through thick vines.")
    if not st.session_state.action_complete:
        left, right = st.columns(2)
        with left:
            chance_encounter(
                "🌿 Cut through",
                "The Dense Jungle",
                "cut through the jungle vines",
                4,
                "The player cuts a safe path through the jungle.",
                "You cut a safe path through the vines.",
                "The player is cut by hidden thorns.",
                "Hidden thorns catch you as you cut through the vines.",
                2,
                "Rusty Machete",
            )
        with right:
            if st.button("➡️ Follow the trail"):
                story = generate_story(
                    "The Dense Jungle",
                    "follow the existing trail",
                    "The player follows the trail safely.",
                    "You follow the trail without disturbing the thick vines.",
                )
                set_result("story", story)
    else:
        show_result()
        show_continue_button()


elif room == "cliff":
    show_room("⛰️ The Cliff", "A steep cliff overlooks the sea. The wind is strong.")
    if "Rusty Machete" in st.session_state.inventory:
        st.info("🗡️ You are carrying a Rusty Machete.")
    if not st.session_state.action_complete:
        left, right = st.columns(2)
        with left:
            if st.button("🪢 Cross the gap"):
                damage = take_damage(2)
                outcome = "The player crosses the cliff gap, loses health, and continues."
                story = generate_story(
                    "The Cliff",
                    "cross the cliff gap",
                    outcome,
                    f"You cross the gap but lose {damage} health. You continue along the cliff.",
                )
                set_result("damage", story, damage)
        with right:
            if st.button("🏃 Run along the edge"):
                outcome = "The player follows the safer trail along the cliff without injury."
                story = generate_story(
                    "The Cliff",
                    "follow the safer trail along the cliff",
                    outcome,
                    "You avoid the dangerous gap and follow the safer trail without losing health.",
                )
                set_result("success", story)
    else:
        show_result()
        show_continue_button()


elif room == "camp":
    show_room("🏕️ The Abandoned Camp", "A red packet rests beneath a torn shelter.")
    if not st.session_state.action_complete:
        left, right = st.columns(2)
        with left:
            if st.button("🌿 Take the herbs"):
                add_item("Healing Herb")
                story = generate_story(
                    "The Abandoned Camp",
                    "take the red packet and find Healing Herbs",
                    "The player takes a packet of Healing Herbs.",
                    "You take the packet and find useful Healing Herbs inside.",
                )
                set_result("item", story, "Healing Herb")
        with right:
            if st.button("➡️ Leave the camp"):
                damage = take_damage(1)
                story = generate_story(
                    "The Abandoned Camp",
                    "leave the camp without taking the Healing Herbs",
                    "The player leaves the Healing Herbs behind and loses health on the journey.",
                    f"You leave the herbs behind. The journey costs you {damage} health.",
                )
                set_result("damage", story, damage)
    else:
        show_result()
        show_continue_button()


elif room == "rescue_point":
    show_room(
        "🚨 The Rescue Point",
        "The island is behind you. At this clearing, send a signal "
        "and wait for rescue to arrive.",
    )
    if not st.session_state.action_complete:
        if "Signal Flare" in st.session_state.inventory:
            if st.button("🚨 Send a rescue signal"):
                story = generate_story(
                    "The Rescue Point",
                    "send the available rescue signal",
                    "The player sends a clear rescue signal and is rescued.",
                    "You send a clear rescue signal. A ship changes course toward you!",
                )
                set_result("win", story)
        else:
            st.error("No rescue can be signaled.")
            story = generate_story(
                "The Rescue Point",
                "arrive at the rescue point without the means to signal",
                "No rescue arrives and the player loses the game.",
                "With no way to signal for help, rescue never finds you.",
            )
            set_result("lose", story)
    else:
        show_result()
        if st.session_state.result_type == "lose":
            if st.button("🔄 Try Again"):
                restart_game()
        elif st.session_state.result_type == "win":
            if st.button("🔄 Play Again"):
                restart_game()
        else:
            if st.button("Continue"):
                st.session_state.result_type = ""
                st.session_state.result_message = ""
                st.session_state.result_value = ""
                st.session_state.action_complete = False
                st.rerun()
