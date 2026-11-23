

import os
import random
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None


st.set_page_config(
    page_title="Stranded Island",
    page_icon="🏝️",
    layout="centered",
)

st.title("🏝️ Stranded Island")

if "game_started" not in st.session_state:
    st.session_state.game_started = False

number_of_rooms = 5

def start_game(player_name):
    st.session_state.game_started = True
    st.session_state.player_name = player_name.strip()

    st.session_state.health = 5
    st.session_state.max_health = 5
    st.session_state.inventory = []
    st.session_state.room_number = 0

    st.session_state.result_type = ""
    st.session_state.result_message = ""
    st.session_state.result_value = ""
    st.session_state.action_complete = False
    st.session_state.escaped = False

def restart_game():
    st.session_state.clear()
    st.rerun()


def clear_result():
    st.session_state.result_type = ""
    st.session_state.result_message = ""
    st.session_state.result_value = ""
    st.session_state.action_complete = False


def continue_game():
    clear_result()
    st.session_state.room_number += 1
    st.rerun()


def set_result(result_type, message, value=""):
    st.session_state.result_type = result_type
    st.session_state.result_message = message
    st.session_state.result_value = value
    st.session_state.action_complete = True

    if result_type == "win":
        st.session_state.escaped = True

    st.rerun()
#add_item() avoids adding the same item twice; has_item() checks whether an item is in the inventory. The health functions keep health within the range of 0 to max_health, and return the actual amount lost or restored.
def add_item(item):
    if item not in st.session_state.inventory:
        st.session_state.inventory.append(item)


def has_item(item):
    return item in st.session_state.inventory


def take_damage(amount):
    old_health = st.session_state.health
    st.session_state.health = max(0, old_health - amount)
    return old_health - st.session_state.health


def heal_player(amount):
    old_health = st.session_state.health
    new_health = min(st.session_state.max_health, old_health + amount)
    st.session_state.health = new_health
    return new_health - old_health




def generate_story(room_name, action, outcome, fallback_message):
    if client is None:
        return fallback_message

    inventory = ", ".join(st.session_state.inventory)
    if not inventory:
        inventory = "Nothing"

    prompt = f"""
You are telling the story for a survival adventure called Stranded Island.
The player survived a plane crash and is trying to get rescued.

Player: {st.session_state.player_name}
Location: {room_name}
Health: {st.session_state.health}/{st.session_state.max_health}
Inventory: {inventory}
Action: {action}
Outcome: {outcome}

Describe what happens in 30-50 words. Use second person and present tense.
Use atmospheric language suitable for all ages. Stay in this location.
Do not invent events or change the outcome, health, or inventory.
"""

    try:
        response = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt,
            generation_config={"thinking_level": "minimal"},
        )

        if response.output_text:
            return response.output_text

        st.warning("Gemini did not return a story. Showing the built-in description.")
    except Exception as error:
        st.error(f"Gemini error: {error}")

    return fallback_message

def finish_action(
    room_name,
    action,
    outcome,
    fallback_message,
    result_type="story",
    result_value="",
):
    story = generate_story(room_name, action, outcome, fallback_message)
    set_result(result_type, story, result_value)


def show_player_info():
    st.subheader(f"🧑 {st.session_state.player_name}")

    left_column, right_column = st.columns(2)

    with left_column:
        st.write(
            f"❤️ Health: {st.session_state.health}/"
            f"{st.session_state.max_health}"
        )

    with right_column:
        inventory = ", ".join(st.session_state.inventory)
        if not inventory:
            inventory = "Empty"
        st.write(f"🎒 Inventory: {inventory}")

    if (
        has_item("First Aid Kit")
        and st.session_state.health < st.session_state.max_health
    ):
        if st.button("🩹 Use First Aid Kit"):
            healed = heal_player(2)
            st.session_state.inventory.remove("First Aid Kit")
            set_result(
                "heal",
                f"You use the First Aid Kit and recover {healed} health.",
                healed,
            )

    current_location = st.session_state.room_number + 1
    st.caption(f"Location {current_location} of {number_of_rooms}")
    st.divider()


def show_result():
    result_type = st.session_state.result_type
    result_value = st.session_state.result_value

    if result_type == "item":
        st.success(f"🎒 ITEM FOUND: {result_value}")
    elif result_type == "damage":
        st.error(f"💔 INJURY: You lose {result_value} health.")
    elif result_type == "heal":
        st.success(f"💚 RECOVERED: You regain {result_value} health.")
    elif result_type == "success":
        st.success("✅ You made it through safely.")
    elif result_type == "win":
        st.success("🛟 Rescue is on the way. You escaped the island!")
    else:
        st.info("The journey continues...")

    st.write(st.session_state.result_message)


def show_continue_button():
    if st.button("Continue"):
        continue_game()

def show_crash_site():
    st.header("✈️ The Crash Site")
    st.write(
        "The damaged plane rests near the shore. "
        "Useful supplies may be inside."
    )

    if not st.session_state.action_complete:
        left_column, right_column = st.columns(2)

        with left_column:
            if st.button("🔎 Search the luggage"):
                add_item("First Aid Kit")
                add_item("Machete")
                finish_action(
                    "the crash site",
                    "search the luggage",
                    "You find a First Aid Kit and a Machete.",
                    "You search the scattered luggage and find a First Aid Kit "
                    "and a Machete.",
                    "item",
                    "First Aid Kit and Machete",
                )

        with right_column:
            if st.button("➡️ Head for the beach"):
                finish_action(
                    "the crash site",
                    "leave the plane and head for the beach",
                    "You leave the crash site and walk toward the beach.",
                    "You leave the wreckage behind and make your way toward "
                    "the beach.",
                )
    else:
        show_result()
        show_continue_button()


def show_beach():
    st.header("🌊 The Beach")
    st.write(
        "The tide has carried pieces of luggage and supplies onto the sand."
    )

    if not st.session_state.action_complete:
        left_column, right_column = st.columns(2)

        with left_column:
            if st.button("🔦 Search the washed-up supplies"):
                add_item("Signal Flare")
                finish_action(
                    "the beach",
                    "search the washed-up supplies",
                    "You find a working Signal Flare among the debris.",
                    "Among the debris, you find a working Signal Flare.",
                    "item",
                    "Signal Flare",
                )

        with right_column:
            if st.button("🌿 Follow a path inland"):
                finish_action(
                    "the beach",
                    "follow a path inland",
                    "You find a narrow trail leading into the jungle.",
                    "You leave the shoreline and follow a narrow trail inland.",
                )
    else:
        show_result()
        show_continue_button()


def show_jungle():
    st.header("🌴 The Jungle Trail")
    st.write("Dense plants block the direct route toward higher ground.")

    if not st.session_state.action_complete:
        left_column, right_column = st.columns(2)

        with left_column:
            if st.button("🌿 Cut through the dense growth"):
                dice_roll = random.randint(1, 6)

                if has_item("Machete"):
                    dice_roll += 2

                if dice_roll >= 4:
                    finish_action(
                        "the jungle trail",
                        "cut through the dense growth",
                        "You clear the trail and reach the other side without injury.",
                        "You push through the undergrowth and reach the other "
                        "side safely.",
                        "success",
                    )
                else:
                    damage = take_damage(2)
                    finish_action(
                        "the jungle trail",
                        "cut through the dense growth",
                        "A hidden branch catches you and leaves you injured.",
                        "The tangled growth hides a sharp branch. You push "
                        "through, but come away injured.",
                        "damage",
                        damage,
                    )

        with right_column:
            if st.button("💧 Follow the stream"):
                finish_action(
                    "the jungle trail",
                    "follow the stream",
                    "You find a safer route that follows the water uphill.",
                    "You avoid the thickest plants by following a stream uphill.",
                )
    else:
        show_result()
        show_continue_button()

def show_spring():
    st.header("💧 The Freshwater Spring")
    st.write(
        "A clear spring emerges from the rocks. You can rest before climbing."
    )

    if not st.session_state.action_complete:
        left_column, right_column = st.columns(2)

        with left_column:
            if st.button("🧘 Rest and drink"):
                healed = heal_player(2)
                finish_action(
                    "the freshwater spring",
                    "rest and drink from the spring",
                    f"You rest and recover {healed} health.",
                    f"You drink the cool water and rest, recovering {healed} health.",
                    "heal",
                    healed,
                )

        with right_column:
            if st.button("➡️ Continue toward the ridge"):
                finish_action(
                    "the freshwater spring",
                    "continue toward the ridge",
                    "You leave the spring and begin climbing toward the ridge.",
                    "You leave the spring and start climbing toward higher ground.",
                )
    else:
        show_result()
        show_continue_button()



def show_ridge():
    st.header("⛰️ The Ridge")
    st.write(
        "Rescuers may spot a signal from here. A flare is reliable; "
        "a smoke signal takes luck."
    )

    if st.session_state.action_complete:
        show_result()

        if st.session_state.escaped:
            if st.button("🔄 Play Again"):
                restart_game()
        elif st.button("Try the signal again"):
            clear_result()
            st.rerun()

        return

    if has_item("Signal Flare"):
        if st.button("🚨 Fire the Signal Flare"):
            finish_action(
                "the ridge",
                "fire the Signal Flare",
                "A rescue crew spots the flare and heads toward the island.",
                "You fire the flare. Its bright trail rises above the trees, "
                "and a rescue crew turns toward the island.",
                "win",
            )

    if st.button("🔥 Build a smoke signal"):
        dice_roll = random.randint(1, 6)

        if has_item("Machete"):
            dice_roll += 1

        if dice_roll >= 4:
            finish_action(
                "the ridge",
                "build a smoke signal",
                "Rescuers see the smoke and head toward the island.",
                "You build a fire on the ridge. Its smoke catches the wind, "
                "and rescuers spot it from the sea.",
                "win",
            )
        else:
            damage = take_damage(1)
            finish_action(
                "the ridge",
                "build a smoke signal",
                "The damp wood will not catch, and the effort leaves you exhausted.",
                "The damp wood refuses to catch. You pause to recover before "
                "trying again.",
                "damage",
                damage,
            )

if not st.session_state.game_started:
    st.write(
        "Your plane has gone down over the ocean. You wake on an unfamiliar "
        "island with one goal: survive long enough to get rescued."
    )

    player_name = st.text_input("What is your name?")

    if st.button("🏝️ Begin your survival"):
        if player_name.strip():
            start_game(player_name)
            st.rerun()
        else:
            st.warning("Enter your name first.")

    st.stop()


show_player_info()

if st.session_state.health <= 0:
    st.header("💀 Lost on the Island")
    st.error("Your strength gives out before help can reach you.")

    if st.button("🔄 Try Again"):
        restart_game()

    st.stop()


if st.session_state.room_number == 0:
    show_crash_site()
elif st.session_state.room_number == 1:
    show_beach()
elif st.session_state.room_number == 2:
    show_jungle()
elif st.session_state.room_number == 3:
    show_spring()
else:
    show_ridge()



