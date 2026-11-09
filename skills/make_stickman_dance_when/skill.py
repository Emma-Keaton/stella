"""
Feature: make_stickman_dance_when
Description: Creates a visual representation of a stickman dancing. This skill is intended to be called when a user explicitly asks for a stickman to dance.
Uses theme tokens from themes.json (no hardcoded colours).
"""

FEATURE_METADATA = {
    "name": "make_stickman_dance_when",
    "description": "Creates a visual representation of a stickman dancing. This skill is intended to be called when a user explicitly asks for a stickman to dance. Colours come from the active theme in themes.json.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "dance_style": {
                "type": "STRING",
                "description": "The style of dance the stickman should perform (e.g., 'floss', 'robot', 'ballet', 'disco'). Defaults to 'disco'.",
            },
            "duration_seconds": {
                "type": "INTEGER",
                "description": "The duration in seconds the stickman should dance. Defaults to 10 seconds.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": ["matplotlib", "numpy"],
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _matplotlib_numpy():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        import numpy as np
        return plt, animation, np
    except Exception:
        return None, None, None


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def execute(**kwargs):
    """Creates a stickman dancing animation GIF."""
    plt, animation, np = _matplotlib_numpy()
    if plt is None or np is None or animation is None:
        return {
            "title": "Stickman Dance Unavailable",
            "summary": "matplotlib and numpy are required to generate the stickman dance animation. Install them to enable this feature.",
        }

    dance_style = kwargs.get("dance_style", "disco")
    duration_seconds = kwargs.get("duration_seconds", 10)

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor(_theme_colour("bg", "#0B0F19"))
    ax.set_facecolor(_theme_colour("surface", "#0B0F19"))
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    plt.style.use("dark_background")

    primary_colour = _theme_colour("primary", "#00F0FF")
    success_colour = _theme_colour("success", "#10B981")
    warning_colour = _theme_colour("warning", "#F59E0B")

    head_center = np.array([0, 0.7])
    neck_pos = head_center + np.array([0, -0.2])
    torso_top = neck_pos + np.array([0, -0.3])
    torso_bottom = torso_top + np.array([0, -0.4])

    head, = ax.plot([], [], "o", color=primary_colour, markersize=15)
    neck, = ax.plot([], [], "-", color=success_colour, linewidth=3)
    torso, = ax.plot([], [], "-", color=success_colour, linewidth=3)
    left_arm_upper, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    left_arm_lower, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    right_arm_upper, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    right_arm_lower, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    left_leg_upper, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    left_leg_lower, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    right_leg_upper, = ax.plot([], [], "-", color=warning_colour, linewidth=3)
    right_leg_lower, = ax.plot([], [], "-", color=warning_colour, linewidth=3)

    frames_data = []

    def get_disco_moves(t, duration):
        angle_offset = np.sin(2 * np.pi * t / duration) * np.pi / 6
        leg_sway = np.sin(2 * np.pi * t / duration * 2) * 0.2
        arm_raise = np.sin(2 * np.pi * t / duration * 1.5) * 0.3
        head_pos = head_center
        neck_pos = head_pos + np.array([0, -0.2])
        torso_top_pos = neck_pos + np.array([0, -0.3])
        torso_bottom_pos = torso_top_pos + np.array([0, -0.4])
        left_shoulder = torso_top_pos + np.array([-0.2, 0.1])
        right_shoulder = torso_top_pos + np.array([0.2, 0.1])
        left_arm_upper_pos = left_shoulder + np.array([arm_raise, -arm_raise])
        left_arm_lower_pos = left_arm_upper_pos + np.array([-0.2, -0.3])
        right_arm_upper_pos = right_shoulder + np.array([-arm_raise, -arm_raise])
        right_arm_lower_pos = right_arm_upper_pos + np.array([0.2, -0.3])
        left_hip = torso_bottom_pos + np.array([-0.1, 0])
        right_hip = torso_bottom_pos + np.array([0.1, 0])
        left_leg_upper_pos = left_hip + np.array([leg_sway, -0.3])
        left_leg_lower_pos = left_leg_upper_pos + np.array([0, -0.4])
        right_leg_upper_pos = right_hip + np.array([-leg_sway, -0.3])
        right_leg_lower_pos = right_leg_upper_pos + np.array([0, -0.4])
        return [
            head_pos, neck_pos, torso_top_pos, torso_bottom_pos,
            left_shoulder, left_arm_upper_pos, left_arm_lower_pos,
            right_shoulder, right_arm_upper_pos, right_arm_lower_pos,
            left_hip, left_leg_upper_pos, left_leg_lower_pos,
            right_hip, right_leg_upper_pos, right_leg_lower_pos
        ]

    def get_floss_moves(t, duration):
        progress = t / duration
        if progress < 0.25:
            arm_angle = np.sin(progress * 4 * np.pi) * np.pi / 2
            leg_pos = np.array([0, -0.3])
        elif progress < 0.5:
            arm_angle = np.pi / 2 + np.sin((progress - 0.25) * 4 * np.pi) * np.pi / 2
            leg_pos = np.array([0.2, -0.3])
        elif progress < 0.75:
            arm_angle = np.pi / 2 + np.sin((progress - 0.5) * 4 * np.pi) * np.pi / 2
            leg_pos = np.array([-0.2, -0.3])
        else:
            arm_angle = np.pi / 2 + np.sin((progress - 0.75) * 4 * np.pi) * np.pi / 2
            leg_pos = np.array([0, -0.3])
        head_pos = head_center
        neck_pos = head_pos + np.array([0, -0.2])
        torso_top_pos = neck_pos + np.array([0, -0.3])
        torso_bottom_pos = torso_top_pos + np.array([0, -0.4])
        left_shoulder = torso_top_pos + np.array([-0.2, 0.1])
        right_shoulder = torso_top_pos + np.array([0.2, 0.1])
        left_arm_upper_pos = left_shoulder + np.array([0, 0.4 * np.sin(arm_angle)])
        left_arm_lower_pos = left_arm_upper_pos + np.array([-0.3 * np.cos(arm_angle), -0.3 * np.sin(arm_angle)])
        right_arm_upper_pos = right_shoulder + np.array([0, 0.4 * np.sin(arm_angle)])
        right_arm_lower_pos = right_arm_upper_pos + np.array([0.3 * np.cos(arm_angle), -0.3 * np.sin(arm_angle)])
        left_hip = torso_bottom_pos + np.array([-0.1, 0])
        right_hip = torso_bottom_pos + np.array([0.1, 0])
        left_leg_upper_pos = left_hip + leg_pos
        left_leg_lower_pos = left_leg_upper_pos + np.array([0, -0.4])
        right_leg_upper_pos = right_hip + np.array([0, -0.3])
        right_leg_lower_pos = right_leg_upper_pos + np.array([0, -0.4])
        return [
            head_pos, neck_pos, torso_top_pos, torso_bottom_pos,
            left_shoulder, left_arm_upper_pos, left_arm_lower_pos,
            right_shoulder, right_arm_upper_pos, right_arm_lower_pos,
            left_hip, left_leg_upper_pos, left_leg_lower_pos,
            right_hip, right_leg_upper_pos, right_leg_lower_pos
        ]

    def get_robot_moves(t, duration):
        phase = t / duration
        angle_offset = np.sin(phase * 4 * np.pi) * np.pi / 4
        leg_offset = np.sin(phase * 6 * np.pi) * 0.3
        head_pos = head_center
        neck_pos = head_pos + np.array([0, -0.2])
        torso_top_pos = neck_pos + np.array([0, -0.3])
        torso_bottom_pos = torso_top_pos + np.array([0, -0.4])
        left_shoulder = torso_top_pos + np.array([-0.2, 0.1])
        right_shoulder = torso_top_pos + np.array([0.2, 0.1])
        left_arm_upper_pos = left_shoulder + np.array([0.1, 0.2])
        left_arm_lower_pos = left_arm_upper_pos + np.array([0.3, -0.3])
        right_arm_upper_pos = right_shoulder + np.array([-0.1, 0.2])
        right_arm_lower_pos = right_arm_upper_pos + np.array([-0.3, -0.3])
        left_hip = torso_bottom_pos + np.array([-0.1, 0])
        right_hip = torso_bottom_pos + np.array([0.1, 0])
        left_leg_upper_pos = left_hip + np.array([leg_offset, -0.3])
        left_leg_lower_pos = left_leg_upper_pos + np.array([0, -0.4])
        right_leg_upper_pos = right_hip + np.array([-leg_offset, -0.3])
        right_leg_lower_pos = right_leg_upper_pos + np.array([0, -0.4])
        return [
            head_pos, neck_pos, torso_top_pos, torso_bottom_pos,
            left_shoulder, left_arm_upper_pos, left_arm_lower_pos,
            right_shoulder, right_arm_upper_pos, right_arm_lower_pos,
            left_hip, left_leg_upper_pos, left_leg_lower_pos,
            right_hip, right_leg_upper_pos, right_leg_lower_pos
        ]

    if dance_style.lower() == "floss":
        get_moves = get_floss_moves
    elif dance_style.lower() == "robot":
        get_moves = get_robot_moves
    else:
        get_moves = get_disco_moves

    num_frames = int(duration_seconds * 30)
    for i in range(num_frames):
        t = (i / num_frames) * duration_seconds
        try:
            positions = get_moves(t, duration_seconds)
            frames_data.append(positions)
        except Exception:
            if frames_data:
                frames_data.append(frames_data[-1])
            else:
                frames_data.append([
                    head_center, neck_pos, torso_top_pos, torso_bottom_pos,
                    torso_top_pos + np.array([-0.2, 0.1]), torso_top_pos + np.array([-0.2, 0.1]), torso_top_pos + np.array([-0.4, -0.1]),
                    torso_top_pos + np.array([0.2, 0.1]), torso_top_pos + np.array([0.2, 0.1]), torso_top_pos + np.array([0.4, -0.1]),
                    torso_bottom_pos + np.array([-0.1, 0]), torso_bottom_pos + np.array([-0.1, -0.4]), torso_bottom_pos + np.array([-0.1, -0.8]),
                    torso_bottom_pos + np.array([0.1, 0]), torso_bottom_pos + np.array([0.1, -0.4]), torso_bottom_pos + np.array([0.1, -0.8])
                ])

    def update(frame_index):
        if frame_index >= len(frames_data):
            return []
        pos = frames_data[frame_index]
        head.set_data([pos[0][0]], [pos[0][1]])
        neck.set_data([pos[1][0], pos[2][0]], [pos[1][1], pos[2][1]])
        torso.set_data([pos[2][0], pos[3][0]], [pos[2][1], pos[3][1]])
        left_shoulder = pos[4]
        left_arm_upper.set_data([left_shoulder[0], pos[5][0]], [left_shoulder[1], pos[5][1]])
        left_arm_lower.set_data([pos[5][0], pos[6][0]], [pos[5][1], pos[6][1]])
        right_shoulder = pos[7]
        right_arm_upper.set_data([right_shoulder[0], pos[8][0]], [right_shoulder[1], pos[8][1]])
        right_arm_lower.set_data([pos[8][0], pos[9][0]], [pos[8][1], pos[9][1]])
        left_hip = pos[10]
        left_leg_upper.set_data([left_hip[0], pos[11][0]], [left_hip[1], pos[11][1]])
        left_leg_lower.set_data([pos[11][0], pos[12][0]], [pos[11][1], pos[12][1]])
        right_hip = pos[13]
        right_leg_upper.set_data([right_hip[0], pos[14][0]], [right_hip[1], pos[14][1]])
        right_leg_lower.set_data([pos[14][0], pos[15][0]], [pos[14][1], pos[15][1]])
        return [
            head, neck, torso, left_arm_upper, left_arm_lower, right_arm_upper, right_arm_lower,
            left_leg_upper, left_leg_lower, right_leg_upper, right_leg_lower
        ]

    ani = animation.FuncAnimation(fig, update, frames=len(frames_data), interval=1000/30, blit=True, repeat=False)

    output_dir = _deliverables_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = str(output_dir / "stickman_dance.gif")

    try:
        ani.save(image_path, writer="pillow", fps=30)
    except Exception:
        try:
            static_image_path = str(output_dir / "stickman_static.png")
            plt.savefig(static_image_path, facecolor=_theme_colour("bg", "#0B0F19"))
            plt.close(fig)
            return {
                "image_path": static_image_path,
                "title": "Stickman Dance Failed",
                "summary": "Could not generate the dancing stickman animation. Here is a static image instead.",
            }
        except Exception:
            plt.close(fig)
            return {
                "image_path": None,
                "title": "Stickman Dance Failed",
                "summary": "Failed to generate stickman dance animation and static fallback.",
            }

    plt.close(fig)
    return {
        "image_path": image_path,
        "title": f"Stickman Doing the {dance_style.capitalize()} Dance!",
        "summary": f"Watch the stickman perform a {dance_style} dance for {duration_seconds} seconds.",
    }
