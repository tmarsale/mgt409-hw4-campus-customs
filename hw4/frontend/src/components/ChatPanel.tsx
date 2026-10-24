import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ApiError,
  CHAT_MAX_CHARS,
  fetchChatHistory,
  formatPrice,
  sendChatMessage,
  type ChatProductCard,
  type ChatTurn,
  type PageResults,
} from "../api";
import { assistantViewUrl, useAssistantResults } from "../assistantResults";
import { useAuth } from "../auth";
import { OPEN_CHAT_EVENT } from "../chatEvents";
import ProductImage from "./ProductImage";

const SMALL_SCREEN = "(max-width: 560px)";

// Quick-start questions shown before the customer has typed anything (Problem 10).
const STARTERS = ["Something cozy for winter", "A gift for my dad", "Show me quarter-zips", "Game-day T-shirts"];
const PRODUCT_STARTERS = ["What colors does this come in?", "Is this in stock in medium?", "What would go well with this?"];

interface Message {
  id: number;
  role: "user" | "assistant" | "error";
  text: string;
  /** Products the assistant looked up and is talking about (built by the backend from the database). */
  products?: ChatProductCard[];
  /** Search results this reply put on the page (so the customer can bring them back). */
  pageResults?: PageResults;
  /** The product(s) this reply was about, sent back with the next message so "it" can be understood. */
  contextIds?: string[];
  /** For error messages: the customer message to send again. */
  retry?: string;
}

const welcomeText = (firstName?: string) =>
  `Hi${firstName ? ` ${firstName}` : ""}! I'm the Campus Customs shopping assistant. Ask me about Yale gear, gift ideas, or what might suit you best.`;

/** Show the assistant's text safely: line breaks are kept and **bold** becomes bold, with no raw HTML. */
function formatText(text: string): ReactNode {
  return text.split("\n").map((line, i) => (
    <Fragment key={i}>
      {i > 0 && <br />}
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith("**") && part.endsWith("**") && part.length > 4 ? <strong key={j}>{part.slice(2, -2)}</strong> : part,
      )}
    </Fragment>
  ));
}

export default function ChatPanel() {
  const { user } = useAuth();
  const { show: showOnPage } = useAssistantResults();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{ id: 0, role: "assistant", text: welcomeText() }]);
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);
  const nextId = useRef(1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // When someone signs in (or out), the window switches conversations: a signed-in customer gets
  // their saved history back from the database; a guest starts fresh. One customer's chat is
  // never shown to the next person using the same browser.
  const [loadingHistory, setLoadingHistory] = useState(false);
  useEffect(() => {
    const welcome: Message = { id: 0, role: "assistant", text: welcomeText(user?.first_name) };
    setMessages([welcome]);
    if (!user) return;
    let cancelled = false;
    setLoadingHistory(true);
    fetchChatHistory()
      .then((saved) => {
        if (cancelled || saved.length === 0) return;
        const restored: Message[] = saved.map((m) => ({
          id: nextId.current++,
          role: m.role,
          text: m.content,
          products: m.products,
          pageResults: m.page_results ?? undefined,
        }));
        setMessages([
          { id: 0, role: "assistant", text: `Welcome back, ${user.first_name}! Here's our conversation so far.` },
          ...restored,
        ]);
      })
      .finally(() => !cancelled && setLoadingHistory(false));
    return () => {
      cancelled = true;
    };
  }, [user?.id, user?.first_name]);

  const onProductPage = /^\/products\/[^/]+$/.test(location.pathname);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open, waiting]);

  // Problem 9: on screens 900px and wider the open chat becomes a sidebar and the page makes room
  // for it (body.chat-docked in index.css), so it never covers the products being browsed.
  useEffect(() => {
    document.body.classList.toggle("chat-docked", open);
    return () => document.body.classList.remove("chat-docked");
  }, [open]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, open, waiting]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const add = (message: Omit<Message, "id">) => setMessages((m) => [...m, { ...message, id: nextId.current++ }]);

  /** Put the assistant's search results on the Products page, without a page refresh. */
  function displayOnPage(results: PageResults) {
    const onAssistantView = location.pathname === "/products" && new URLSearchParams(location.search).get("view") === "assistant";
    if (results.total === 0) {
      // Nothing matched. If earlier assistant results are on screen, replace them with a clear
      // "no matching products" message, but don't move the customer to an empty page.
      if (onAssistantView) {
        showOnPage(results);
        navigate(assistantViewUrl(results.query), { replace: true });
      }
      return;
    }
    showOnPage(results);
    // The search is kept in the address, so the results come back after a refresh.
    navigate(assistantViewUrl(results.query));
    // On a phone the chat covers the page, so step aside to reveal the results (the chat is kept).
    if (window.matchMedia(SMALL_SCREEN).matches) setOpen(false);
  }

  async function ask(text: string, earlier: Message[]) {
    // Send the real conversation for context: the welcome note and error notices are left out.
    const history: ChatTurn[] = earlier
      .filter((m) => m.id !== 0 && m.role !== "error")
      .map((m) => ({
        role: m.role as ChatTurn["role"],
        content: m.text,
        ...(m.role === "assistant" && m.contextIds?.length ? { product_ids: m.contextIds } : {}),
      }));
    setWaiting(true);
    try {
      const { reply, products, page_results, context_product_ids } = await sendChatMessage(text, history, location.pathname);
      add({ role: "assistant", text: reply, products, pageResults: page_results ?? undefined, contextIds: context_product_ids });
      if (page_results) displayOnPage(page_results);
    } catch (err) {
      const reason =
        err instanceof ApiError && err.status !== 422
          ? err.message
          : err instanceof ApiError
            ? "That message couldn't be sent. Please shorten it and try again."
            : "We couldn't reach the shopping assistant. Check your connection and try again.";
      add({ role: "error", text: reason, retry: text });
    } finally {
      setWaiting(false);
    }
  }

  function sendText(text: string) {
    if (!text || waiting) return;
    const earlier = messages;
    add({ role: "user", text });
    setDraft("");
    void ask(text, earlier);
  }

  function send(e: FormEvent) {
    e.preventDefault();
    sendText(draft.trim());
  }

  // Other parts of the site (e.g. "Ask our assistant" buttons) can open the chat and ask a question.
  const sendTextRef = useRef(sendText);
  sendTextRef.current = sendText;
  useEffect(() => {
    const onOpen = (e: Event) => {
      setOpen(true);
      const message = (e as CustomEvent<{ message?: string }>).detail?.message;
      if (message) sendTextRef.current(message);
    };
    window.addEventListener(OPEN_CHAT_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_CHAT_EVENT, onOpen);
  }, []);

  const fresh = !waiting && !loadingHistory && messages.every((m) => m.id === 0);
  const starters = onProductPage ? PRODUCT_STARTERS : STARTERS;

  function retry(message: Message) {
    if (!message.retry || waiting) return;
    const earlier = messages.filter((m) => m.id !== message.id);
    // The customer's original message is already on screen just above the error; resend it.
    setMessages(earlier);
    const withoutLastUser = earlier.slice(0, earlier.map((m) => m.role).lastIndexOf("user"));
    void ask(message.retry, withoutLastUser);
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" role="dialog" aria-label="Shopping assistant">
          <header className="chat-header">
            <span className="chat-avatar" aria-hidden="true">
              CC
              <span className="chat-online" />
            </span>
            <div className="chat-heading">
              <p className="chat-title">Shopping Assistant</p>
              <p className="chat-subtitle">
                {user ? "Chat saved to your account" : "Guest chat · not saved"}
                {onProductPage && " · knows this product"}
              </p>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>
          <div className="chat-messages" ref={listRef} aria-live="polite">
            {messages.map((m) =>
              m.role === "error" ? (
                <div key={m.id} className="chat-bubble chat-error" role="alert">
                  <span>{m.text}</span>
                  {m.retry && (
                    <button className="chat-retry" onClick={() => retry(m)} disabled={waiting}>
                      Try again
                    </button>
                  )}
                </div>
              ) : (
                <Fragment key={m.id}>
                  <p className={`chat-bubble chat-${m.role}`}>{m.role === "assistant" ? formatText(m.text) : m.text}</p>
                  {m.pageResults && m.pageResults.total > 0 && (
                    <button className="chat-page-link" onClick={() => displayOnPage(m.pageResults!)}>
                      View {m.pageResults.total} {m.pageResults.total === 1 ? "product" : "products"} on the page →
                    </button>
                  )}
                  {m.products && m.products.length > 0 && (
                    <div className="chat-products" aria-label="Products mentioned">
                      {m.products.map((p) => (
                        <Link key={p.product_id} to={p.url} className="chat-product">
                          <ProductImage src={p.image_url} alt="" className="chat-product-photo" />
                          <span className="chat-product-name">{p.name}</span>
                          <span className="chat-product-price">{formatPrice(p.price)}</span>
                        </Link>
                      ))}
                    </div>
                  )}
                </Fragment>
              ),
            )}
            {fresh && (
              <div className="chat-starters" aria-label="Suggested questions">
                {starters.map((q) => (
                  <button key={q} className="chat-starter" onClick={() => sendText(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            {waiting && (
              <p className="chat-bubble chat-assistant chat-typing" aria-label="The assistant is typing">
                <span />
                <span />
                <span />
              </p>
            )}
          </div>
          <form className="chat-form" onSubmit={send}>
            <label htmlFor="chat-input" className="visually-hidden">
              Type your message
            </label>
            <input
              id="chat-input"
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={
                waiting
                  ? "The assistant is replying…"
                  : loadingHistory
                    ? "Loading your conversation…"
                    : onProductPage
                      ? "Ask about this product…"
                      : "Ask about styles, gifts, sizing…"
              }
              autoComplete="off"
              maxLength={CHAT_MAX_CHARS}
              disabled={waiting}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={!draft.trim() || waiting}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        className={`chat-toggle ${open ? "is-open" : ""}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? "Close shopping assistant" : "Open shopping assistant"}
      >
        {open ? (
          <span aria-hidden="true" className="chat-toggle-x">
            ×
          </span>
        ) : (
          <>
            <svg aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.9">
              <path d="M21 12a8 8 0 0 1-11.8 7L4 20l1.1-4.6A8 8 0 1 1 21 12z" strokeLinejoin="round" />
            </svg>
            <span className="chat-toggle-label">Ask our assistant</span>
          </>
        )}
      </button>
    </div>
  );
}
