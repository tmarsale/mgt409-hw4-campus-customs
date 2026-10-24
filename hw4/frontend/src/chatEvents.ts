// Lets any page open the shopping assistant (and optionally ask it something) without sharing state.
// The chat panel listens for this event; pages call openChat("…") from a button.

export const OPEN_CHAT_EVENT = "campus-customs:open-chat";

export function openChat(message?: string) {
  window.dispatchEvent(new CustomEvent(OPEN_CHAT_EVENT, { detail: { message } }));
}
