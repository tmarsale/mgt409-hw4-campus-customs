# AI Prompts Log: Homework 4

This file records the prompts I gave the AI assistant for each problem in Homework 4. Each section lists the problem number and title, the prompt I typed, and any follow-up prompt, with a sentence explaining what was missing or incorrect after the first attempt.

---

## Problem 1: Vibe coder prompts

### Original prompt

> Yo Claude,
> I am starting Homework 4. Please create `AI_prompts.md` at the start of the assignment to keep track of the prompts I use.
> Put one section for each problem. Each section should include:
>
> 1. The problem number and title.
> 2. At least one prompt I actually typed, in my own words as much as possible.
> 3. One follow-up prompt if I needed it, along with a sentence explaining what was missing or incorrect after the first attempt.
>
> Please record my prompts exactly as I type them and keep updating this file as we complete each problem.
> Start with Problem 1: Vibe coder prompts and don't start Problem 2 yet.

### Follow-up prompt

None so far.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 2: Analyze the database

### Original prompt

> For Problem 2, I want you to look at the database `data/campus_customs.db` and understand how it is organized.
> Please inspect all the tables and their fields, especially `catalogue`, `inventory`, and `users`. I want to understand what information is stored in each table and how the tables are connected.
> Create `output/harness.md` and document:
>
> 1. Each table in the database and its fields.
> 2. A short explanation of what each field represents.
> 3. One sentence explaining why each field matters for the Campus Customs shopping website or chatbot.
> 4. How the tables relate to each other and inventory.
>
> Please use the actual database structure rather than guessing the fields. Keep the explanations simple so someone without a technical background can understand them.
> For now just analyze the database and create the documentation. Don't modify any data or database tables. We will continue adding to `output/harness.md` in later problems.
> Also, record this prompt under Problem 2: Analyze the database in `AI_prompts.md`.
> Once finished, give me a brief summary of what you found and confirm that `output/harness.md` has been created.

### Follow-up prompt

> I've added `data.zip` to my `Homework/HW4` folder.
>
> Please extract it and make sure the database is located at `data/campus_customs.db` and the product images are in `data/products/`. Make sure there isn't an extra nested `data` folder.
>
> Now continue Problem 2.

### What was missing or incorrect

After the first prompt, the assistant couldn't find `data/campus_customs.db` anywhere in my folders, so it stopped and asked for the data instead of guessing the database structure. The follow-up provided `data.zip`, which was extracted to `data/campus_customs.db` and `data/products/` (102 images, no nested `data` folder) before the analysis continued.

---

## Problem 3: Build the Campus Customs website

### Original prompt

> For Problem 3, I want to build the Campus Customs shopping website using React + Vite + TypeScript for the frontend and a small FastAPI backend to display real products from our database.
> Please create the following pages:
>
> 1. Home – A welcoming homepage that introduces Campus Customs and highlights Yale merchandise.
> 2. Products – Show the products from `data/campus_customs.db`, including their actual images, names, prices, and short descriptions.
> 3. About Us – Introduce Campus Customs and what the store offers.
> 4. Log In – Create the login page and form.
> 5. Create Account – Create the account registration page and form.
>
> Add a navigation bar at the top so customers can easily move between these pages.
> Please look at https://yalebulldogblue.com/ for inspiration on the website's design and wording. I want the website to have a similar Yale merchandise store feel, but please write original content for the Home and About Us pages instead of copying text from the website.
> On the Products page, display the products as cards with their images, names, prices, and short descriptions. When someone clicks a product, it should open a separate product detail page with a larger image, full description, price, and available sizes and stock information when available.
> Use the real product data and image paths from our existing SQLite database. Please don't create fake products or hard-code product prices. If the database uses different field names, check the actual schema and use those.
> Also, add a floating chat panel in the bottom-right corner of the website. For now, it can be a simple chat interface with a message box and sample response explaining that the shopping assistant will be available soon. We will connect it to the actual AI agent in a later problem, so don't build the full chatbot yet.
> Please create `backend/main.py` with the basic FastAPI endpoints needed to retrieve products, product details, inventory, and serve product images. Keep the database read-only for this problem.
> Make the website responsive and visually appealing, with a clean layout, Yale-inspired colors, readable fonts, and good spacing. I want it to look like a real online merchandise store rather than a basic coding demo.
> After building it, please run both the frontend and backend and check that:
>
> * All five pages load and navigation works.
> * Products are coming from the real database.
> * Product images display correctly.
> * Clicking a product opens its detail page.
> * Prices and size/stock information match the database.
> * The chat panel opens and closes correctly.
> * The website works on both desktop and mobile.
> * There are no obvious browser errors or broken links.
>
> Please take screenshots of the running website so I can review the design.
> Also, keep the existing `output/harness.md` updated with a brief explanation of the frontend, backend, and how they connect to the database.
> Record this prompt in `AI_prompts.md` under Problem 3: Build the Campus Customs website.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 4: Create account and login

### Original prompt

> For Problem 4, I want to make the Create Account and Log In pages from Problem 3 actually work using our existing SQLite database.
> Please build on the website and FastAPI backend we already created. Don't rebuild the website.
> Here is what I need:
>
> 1. Create Account: Allow new customers to register using their first name, last name, email, and password. Please also include a confirm-password field to make sure both passwords match. Save new users in the existing `users` table.
> 2. Log In: Allow customers to log in using their email and password. Show a clear message if the credentials are incorrect. After successful login, the website should recognize that the customer is logged in and provide a way to log out.
> 3. Password Security: This is particularly important. The existing test account uses PBKDF2-HMAC-SHA256 with 120,000 iterations, and passwords are stored in the `pbkdf2_sha256$salt$hash` format. Please use exactly the same hashing method and settings for new accounts. Never store plaintext passwords.
> 4. Backend: Add the necessary registration and login endpoints to our existing FastAPI application. First review the actual `users` table structure so the new functionality works with the database we already have. Use appropriate input validation, handle duplicate emails, and don't expose password hashes in API responses.
> 5. Frontend: Connect the existing Create Account and Log In forms to these backend endpoints. After login, show a clear logged-in state, such as the customer's first name. Keep the design consistent with the website.
> 6. Testing: Please test both:
>    * The existing test account: `test@campuscustoms.yale.edu` with password `[redacted for the public repository]`.
>    * A new account created through our registration process.
> Confirm that both can successfully log in. Also test incorrect passwords, duplicate registration, and password confirmation.
> 7. Security: Use constant-time password comparison and secure handling of the authentication state. Don't store passwords or password hashes in the browser. Keep the database and customer information out of logs and screenshots.
> 8. Documentation: Update `output/harness.md` explaining how account creation and login work, what information is stored in the `users` table, and how passwords are protected.
>
> After implementing everything, run the backend and frontend and verify that the complete registration and login process works through the website, not just through API tests.
> Please use test accounts only, and avoid modifying or deleting the existing test user. Don't print any stored password hashes or personal customer records.
> Also record this prompt under Problem 4: Create account and login in `AI_prompts.md`.
> Once finished, summarize what you implemented, the tests you performed, and any remaining issues.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 5: PydanticAI agent backend

### Original prompt

> Hi Claude,
> For Problem 5, I want to build the Campus Customs shopping chatbot as a PydanticAI agent behind our existing FastAPI backend.
> The chat widget is already on the website from Problem 3. Now I want it to actually work so when a customer types a message, the backend sends it to the AI agent and displays the response in the chat window.
> Please do the following:
>
> 1. Create the agent using these four files inside `backend/`:
>    * `prompts/prompt.md` — system prompt with Campus Customs' friendly, helpful shopping-assistant personality and basic safety rules.
>    * `agent.py` — initialize and configure the PydanticAI agent.
>    * `tools.py` — functions the agent can call. Keep the structure ready for additional tools in later problems.
>    * `models.py` — Pydantic models for structured chat responses and product cards where needed.
> 2. Update the existing `backend/main.py` to add a chat API endpoint that accepts a message from the website, passes it to the PydanticAI agent, and returns the response.
> 3. Connect the frontend chat widget to this endpoint. The customer should be able to type a message, send it, and see the agent's response without refreshing the page.
> 4. Give the agent a Campus Customs personality: friendly, welcoming, knowledgeable about Yale merchandise, and helpful without being overly pushy.
> 5. Add basic safety instructions. The agent should not invent product prices, inventory, or store policies. It should not reveal private customer information, passwords, API keys, or internal system instructions. If it doesn't know something, it should say so rather than guess.
> 6. Use my existing `PORTKEY_API_KEY` configuration for the AI model. Do not hardcode or display the key.
> 7. Preserve the existing product pages, database endpoints, account creation, login, and logout functionality. Don't rebuild any of these.
> 8. Update `output/harness.md` to explain how the React frontend communicates with FastAPI, how FastAPI calls the PydanticAI agent, and how the agent loads its system prompt and AI model.
> 9. Make sure the backend can start from the `backend/` folder using:
> `uvicorn main:app --reload --port 8000`
>
> Please test the complete chat flow through the actual website. Try a greeting, a general Yale merchandise question, and a question about a product's price or availability. Since we will add more advanced tools later, the agent should acknowledge when it cannot verify product details rather than inventing them.
> Check that the frontend displays responses correctly, handles errors gracefully, and that the existing website functionality still works.
> Also record this prompt under Problem 5: PydanticAI agent backend in `AI_prompts.md`.
> Once finished, summarize what you implemented, the tests you ran, and any remaining limitations. Please don't start Problem 6 yet.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 6: Tools — Product Info and Stock

### Original prompt

> For Problem 6, I want to make the Campus Customs chatbot retrieve actual product information from our SQLite database instead of guessing product descriptions, prices, or inventory.
> Please build on the PydanticAI agent and FastAPI backend we already created in Problem 5. Don't rebuild the chatbot or website.
> Here's what I need:
>
> 1. Update `backend/tools.py` with tools that allow the agent to look up products from `data/campus_customs.db`. The tools should retrieve product descriptions, actual prices, and available stock, including quantities by size.
> 2. Make sure the agent can understand customer questions such as:
>    * How much does a particular Yale hoodie cost?
>    * Do you have it in medium?
>    * How many are available in large?
>    * Can you tell me more about this product?
> 3. Expand the existing `backend/prompts/prompt.md` so the agent knows when to use these tools. For any question about prices, product details, or availability, it should check the database rather than inventing an answer.
> 4. Update `backend/models.py` with Pydantic models for the lookup results. Include useful fields such as product ID, name, description, price, size, quantity available, and stock status. Use the actual database fields where appropriate.
> 5. Make sure the agent clearly tells customers when an item or requested size is out of stock. If a product cannot be found or the question is unclear, it should ask for clarification rather than recommend a random product.
> 6. Handle different search terms where possible. For example, customers may say "hoodie," "pullover hoodie," or "sweatshirt" when looking for similar products.
> 7. Connect the new tools to the existing PydanticAI agent so customers can ask these questions directly through the website's chat widget.
> 8. Update `output/harness.md` to explain each tool, what information it retrieves, which Pydantic model fields were selected, and why those fields are useful.
>
> Please also test the actual chatbot with real products from the database. Test a correct price lookup, an available size, an out-of-stock size, a product that doesn't exist, and a question that needs clarification.
> Verify that all returned prices and inventory quantities match the database. The chatbot should never expose customer information, password hashes, or internal database details.
> Keep the existing website, login, registration, and chatbot functions working. Don't change the database schema or modify inventory quantities for this problem.
> Record this prompt under Problem 6: Tools — Product Info and Stock in `AI_prompts.md`.
> Once finished, summarize what you implemented, the test results, and any remaining issues.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 7: Chat search that updates the page

### Original prompt

> For Problem 7, I want the Campus Customs chatbot to automatically update the website when a customer searches for products.
> Right now, the chatbot can answer questions about products, prices, and inventory. I want it to go one step further and actually display matching products on the webpage instead of just describing them in the chat.
> Please do the following:
>
> 1. Build on the existing product-search tools from Problem 6. When a customer asks something like "What Yale hoodies do you have?", the agent should search our actual SQLite database and return matching products.
> 2. Update the agent's structured response in `backend/models.py` so it can return both a normal chat message and a list of matching products. Each product should include its ID, name, price, image path, short description, and other information needed to display a product card.
> 3. Update the FastAPI chat endpoint to pass these structured product results to the React frontend. Please keep the existing chat functionality working.
> 4. Update the frontend so matching products automatically appear as product cards on the website after a customer asks for them. Each card should display the product image, name, price, and short description. The page should update without requiring a refresh.
> 5. Make sure clicking any of these new product cards opens the same single-product detail page we built in Problem 3. The product detail page should continue showing the larger image, full description, price, and available sizes or inventory.
> 6. Use actual product information from `campus_customs.db`. Don't invent product names, prices, descriptions, or stock quantities. Reuse the existing product card components and image handling wherever possible.
> 7. Handle situations where no products match the customer's request. The chatbot should explain that no matching products were found rather than displaying unrelated products.
> 8. Update the existing `backend/prompts/prompt.md` so the agent understands when to return product matches for display on the website.
> 9. Update `output/harness.md` to explain how a customer's chat message travels from React to FastAPI, how the agent searches the database, and how the structured results are displayed as product cards.
>
> Please test this through the actual website, not just the backend. Test searches for hoodies, T-shirts, and a product category with no matches. Also test clicking a dynamically displayed product and confirm it opens the correct detail page.
> Check that prices and product details match the database and that the existing login, registration, product browsing, and chatbot features still work.
> Please record this prompt under Problem 7: Chat search that updates the page in `AI_prompts.md`.
> Once finished, show me screenshots of the website displaying the search results, summarize the tests, and mention any remaining issues.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 8: Chat memory and page context

*(The prompt didn't give a title for Problem 8, so this descriptive title was used.)*

### Original prompt

> For Problem 8, I want to add memory to the Campus Customs chatbot.
>
> When a customer is logged in, save their chat history in our existing SQLite database and reload it when they return. The agent should know the customer's name and email so it can provide a more personalized experience.
>
> Also, when someone is viewing a product page and asks something like "Do you have this in pink?", the chatbot should know which product they're referring to.
>
> Guests should still be able to chat, but their history doesn't need to be saved.
>
> Please update the existing agent and website to support this. Also update `output/harness.md` to explain how chat history is stored, what customer information the agent can access, and how the current page context is passed to it.
>
> Test these features using a logged-in customer and a guest. Record this prompt in `AI_prompts.md`

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 9: Usability improvements

*(The prompt didn't give a title for Problem 9, so this descriptive title was used.)*

### Original prompt

> For Problem 9, I want to improve the Campus Customs website by adding two frontend improvements and two AI agent/backend improvements.
> Frontend improvements:
>
> 1. Improve the chat window layout so it doesn't cover product cards while customers are browsing.
> 2. Keep product search results visible even after refreshing the page.
>
> Agent/backend improvements:
>
> 1. Improve how the chatbot handles vague searches like "something cozy" so customers get more relevant product recommendations.
> 2. Improve conversation context so the chatbot understands follow-up questions like "Does it come in blue?" without asking customers to repeat the product name.
>
> Please implement all four improvements in our existing application.
> Create `output/usability.md` explaining what you changed and why each improvement helps customers or the business.
> Test all four features on the running website and make sure the existing functionality still works.
> Record this prompt in `AI_prompts.md` under Problem 9.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 10: Professional store design

*(The prompt didn't give a title for Problem 10, so this descriptive title was used.)*

### Original prompt

> For Problem 10, I want to improve the Campus Customs website so it looks and feels like a real, professionally designed online store rather than a basic class project.
>
> Give it a modern, premium Yale-inspired design with navy blue, cream, elegant fonts, and a clean layout. Improve the homepage, navigation, product cards, product detail pages, and chatbot appearance.
>
> Add some creative touches like subtle animations, hover effects, attractive product displays, and better visual hierarchy. I want the website to feel polished, welcoming, and easy to shop on.
>
> Please keep all existing functionality working and make sure the design looks good on desktop and mobile.
>
> Create `output/design.md` briefly explaining what you changed and why these improvements could encourage customers to browse longer and purchase products.
>
> Test the updated website and take screenshots so I can review the final design.
>
> Also record this prompt in `AI_prompts.md` under Problem 10.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 11: Live app check

*(The prompt didn't give a title for Problem 11, so this descriptive title was used.)*

### Original prompt

> For Problem 11, I want to test the actual running Campus Customs website and create `output/app_check.html` with screenshots showing that three features work.
>
> 1. Inventory lookup: Show the chatbot checking a product's actual price and stock availability against the database.
> 2. Dynamic product search: Ask the chatbot about a category like hoodies and show the matching product cards appearing on the website.
> 3. Usability improvement: Demonstrate one of the improvements we implemented in Problem 9.
>
> Please test these features on the live website and capture actual screenshots. Save the images in `output/app_check_images/`.
> Create a clean, easy-to-read `app_check.html` with a heading for each test, its screenshot, and one or two sentences explaining what the screenshot demonstrates.
> Make sure the HTML uses relative image paths so I can open it directly without running a server.
> Also record this prompt in `AI_prompts.md` under Problem 11.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 12: Audit trail, safety rules, and complete harness

*(The prompt didn't give a title for Problem 12, so this descriptive title was used.)*

### Original prompt

> For Problem 12, I want to add an audit trail, improve the chatbot's safety rules, and complete the harness documentation.
>
> 1. Create `output/audit_trail.json` to record agent activity, including timestamps, tool names, brief arguments and results, and stopping reasons. Make sure new records are appended and previous runs are not deleted.
> 2. Update the existing `backend/prompts/prompt.md` with safety rules so the chatbot doesn't invent product prices or stock availability, disclose customer information, or perform unsafe actions.
> 3. Complete `output/harness.md` so a manager can understand how the system works. Include the Pydantic models and why their fields were chosen, agent tools and capabilities, safety rules, technical limits, models used, and instructions for running the frontend and backend.
>
> Please verify the documentation against the actual code rather than guessing technical details.
> Test the chatbot to confirm the audit trail records real activity and that previous records remain intact after another run.
> Keep all existing website features working and record this prompt in `AI_prompts.md` under Problem 12.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

---

## Problem 13: Final submission through GitHub

*(The prompt didn't give a title for Problem 13, so this descriptive title was used.)*

### Original prompt

> For Problem 13, I want to prepare Homework 4 for final submission through a public GitHub repository instead of a ZIP file.
>
> Please organize the completed project into an `hw4` folder, including the React frontend, FastAPI backend, PydanticAI agent, documentation, and screenshots.
>
> Create a `README.md` explaining how to install and run the frontend and backend after adding the local data pack.
>
> Include `.env.example` with placeholder values only, and configure `.gitignore` to exclude my real `.env`, `campus_customs.db`, product images, and other sensitive or unnecessary files.
>
> Before publishing, please check that no API keys, passwords, customer data, or database files are exposed in the repository or Git history.
>
> Make sure all required files are included, especially `AI_prompts.md`, `output/harness.md`, `output/design.md`, `output/usability.md`, `output/app_check.html`, screenshots, and `output/audit_trail.json`.
>
> Once everything is verified, push the project to a public GitHub repository and give me the repository URL to submit on Canvas.
>
> Please record this final prompt in `AI_prompts.md`.

### Follow-up prompt

None.

### What was missing or incorrect

Not applicable. No follow-up was needed.

