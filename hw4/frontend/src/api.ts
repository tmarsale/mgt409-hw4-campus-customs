// Types and calls for the Campus Customs FastAPI backend (backend/main.py).
// Field names match the database's `catalogue` and `inventory` tables.

export interface SizeStock {
  size: string;
  quantity: number;
  in_stock: boolean;
}

export interface ProductSummary {
  product_id: string;
  name: string;
  garment_type: string;
  description: string;
  colors: string[];
  search_tags: string[];
  price: number;
  image_url: string;
  total_stock: number;
}

export interface ProductDetail extends ProductSummary {
  inventory: SizeStock[];
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(response.status === 404 ? "not-found" : `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const fetchProducts = () => getJson<ProductSummary[]>("/api/products");
export const fetchProduct = (id: string) => getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`);

export const formatPrice = (price: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(price);

// The database labels the same kind of garment in several ways ("hoodie", "pullover hoodie",
// "short-sleeve T-shirt", "t-shirt", ...). These shop categories group them for browsing.
export const CATEGORIES = [
  { slug: "hoodies", label: "Hoodies" },
  { slug: "sweatshirts", label: "Crewnecks & Sweatshirts" },
  { slug: "quarter-zips", label: "Quarter-Zips" },
  { slug: "tees", label: "T-Shirts" },
  { slug: "long-sleeve", label: "Long Sleeve" },
  { slug: "outerwear", label: "Jackets & Fleece" },
] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];

export function categoryOf(garmentType: string): CategorySlug {
  const t = garmentType.toLowerCase();
  if (t.includes("hood")) return "hoodies";
  if (t.includes("quarter-zip")) return "quarter-zips";
  if (t.includes("jacket")) return "outerwear";
  if (t.includes("t-shirt")) return "tees";
  if (t.includes("long-sleeve")) return "long-sleeve";
  return "sweatshirts";
}

export const categoryLabel = (slug: CategorySlug) => CATEGORIES.find((c) => c.slug === slug)?.label ?? slug;

export const LOW_STOCK = 3;

// ---- Customer accounts (backend/auth.py) ----
// The session lives in an HttpOnly cookie set by the backend; the website never sees or stores
// the token, the password, or the password hash. Only the fields below are kept, in memory.

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface RegisterInput {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

/** An error from the backend, with any per-field messages (e.g. { email: "Enter a valid email address." }). */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

const UNREACHABLE = "We couldn't reach the store right now. Please try again in a moment.";

async function send<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.ok) return (response.status === 204 ? undefined : await response.json()) as T;

  const data = await response.json().catch(() => ({}));
  const fields: Record<string, string> = {};
  // No explanation from our backend (e.g. it isn't running and the dev server answered instead).
  let message = response.status >= 500 ? UNREACHABLE : "Something went wrong. Please try again.";
  if (typeof data.detail === "string") {
    message = data.detail;
  } else if (Array.isArray(data.detail)) {
    // FastAPI validation errors: [{ loc: ["body", "email"], msg: "Value error, ..." }, ...]
    for (const err of data.detail) {
      const field = err.loc?.[err.loc.length - 1];
      const text = String(err.msg ?? "").replace(/^Value error, /, "");
      if (typeof field === "string" && field !== "body") fields[field] = fields[field] ?? text;
      else message = text;
    }
    if (Object.keys(fields).length) message = "Please fix the highlighted fields.";
  }
  throw new ApiError(message, response.status, fields);
}

export const fetchCurrentUser = async (): Promise<User | null> => {
  const response = await fetch("/api/auth/me", { credentials: "same-origin" });
  return response.ok ? ((await response.json()) as User | null) : null; // null = not signed in
};
export const loginRequest = (email: string, password: string) => send<User>("/api/auth/login", { email, password });
export const registerRequest = (input: RegisterInput) => send<User>("/api/auth/register", input);
export const logoutRequest = () => send<void>("/api/auth/logout");

// ---- Shopping-assistant chat (POST /api/chat → PydanticAI agent) ----

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  /** Assistant turns: the product(s) that reply was about, so guests' follow-ups ("Does it come in blue?") work. */
  product_ids?: string[];
}

export interface ChatProductCard {
  product_id: string;
  name: string;
  price: number;
  image_url: string;
  url: string;
}

/** A product the assistant found, shaped like ProductSummary so the existing ProductCard can show it. */
export interface DisplayProduct extends ProductSummary {
  short_description: string;
  sizes_in_stock: string[];
  url: string;
}

export interface PageResults {
  query: string;
  total: number;
  products: DisplayProduct[];
}

export interface ChatReply {
  reply: string;
  products: ChatProductCard[];
  page_results: PageResults | null;
  /** True when this exchange was saved to the signed-in customer's account. */
  saved: boolean;
  /** The product(s) the conversation is now about (sent back on the next request for guests). */
  context_product_ids: string[];
}

export interface SavedMessage {
  role: "user" | "assistant";
  content: string;
  products: ChatProductCard[];
  page_results: PageResults | null;
  created_at: string;
}

export const CHAT_MAX_CHARS = 1000;
export const CHAT_HISTORY_TURNS = 20;

/**
 * Send a chat message. `pagePath` tells the assistant which page the customer is viewing (so "this"
 * on a product page means that product). `history` is only used for guests; signed-in customers'
 * history comes from the database.
 */
export const sendChatMessage = (message: string, history: ChatTurn[], pagePath: string) =>
  send<ChatReply>("/api/chat", { message, history: history.slice(-CHAT_HISTORY_TURNS), page: { path: pagePath } });

/**
 * Re-run an assistant search by its query (GET /api/search), so assistant results on the Products page
 * survive a refresh or a shared link. Uses the same search and the same "good match only" rule as the chat.
 */
export const fetchAssistantResults = (query: string) => getJson<PageResults>(`/api/search?q=${encodeURIComponent(query)}`);

/** The signed-in customer's saved conversation (empty for guests). */
export const fetchChatHistory = async (): Promise<SavedMessage[]> => {
  const response = await fetch("/api/chat/history", { credentials: "same-origin" });
  if (!response.ok) return [];
  const data = (await response.json()) as { signed_in: boolean; messages: SavedMessage[] };
  return data.messages;
};
