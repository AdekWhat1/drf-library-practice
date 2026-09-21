# 📚 Library Service API

A modern RESTful API for online book borrowing management, automated Telegram notifications, and Stripe Checkout payment processing.

The system replaces manual paper-based library records by managing book inventory, tracking loan periods, computing fines for late returns, and handling payments securely.

---

## 🚀 Key Features

* **Books Service:** Full CRUD operations, inventory tracking (availability checks, automatic stock decrement/increment).
* **Users Service:** Custom user model (email-based authentication), JWT token authentication, profile management.
* **Borrowing Management:**
  * Borrowing creation with real-time stock validation.
  * Automatic Stripe Checkout session generation upon borrowing.
  * Active status and user ID filtering for administrators.
  * Book return action with automatic inventory release and fine generation on overdue returns.
* **Payment Service (Stripe Integration):**
  * Automated payment session creation (`PAYMENT` and `FINE` types).
  * Webhook-less callback verification via `success` and `cancel` endpoints.
  * Fine calculation formula: `overdue_days * daily_fee * FINE_MULTIPLIER`.
  * In-depth nesting of payment history inside borrowing details.
* **Notifications Service (Telegram Bot):**
  * Real-time notifications on new borrowings created (with Stripe payment link).
  * Notifications on successful payments and late return fines.
  * Management command for daily checking and notifying about overdue loans.
* **API Documentation:** OpenAPI 3.0 schema generation with interactive Swagger UI and Redoc via `drf-spectacular`.
* **Testing & Quality Assurance:** Over 80% test coverage using `coverage` with isolated unit and API tests.

---

## 🛠 Tech Stack

* **Backend:** Python 3.12+, Django 5.x / 6.x, Django REST Framework (DRF)
* **Authentication:** `djangorestframework-simplejwt`
* **Payment Gateway:** Stripe API SDK
* **Notifications:** Telegram Bot API
* **API Documentation:** `drf-spectacular` (Swagger UI & Redoc)
* **Database:** PostgreSQL (production / Docker) / SQLite (development)
* **Code Quality & Testing:** `coverage`, `unittest`, `unittest.mock`

---

## ⚙️ Installation & Local Setup

### 1. Clone the repository
```bash
git clone [https://github.com/](https://github.com/)<your-username>/library-service.git
cd library-service

2. Set up virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Configure environment variablesCreate a .env file in the project root based on .env.sample:
cp .env.sample .env
Fill in the credentials:STRIPE_PUBLISHABLE_KEY & STRIPE_SECRET_KEY (from Stripe Dashboard Test Mode)
TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID (from Telegram BotFather and Chat ID bot)

5. Apply database migrations
python manage.py migrate

6. Populate database & create adminBash# Populate initial books sample data:
python manage.py populate_db
# Create superuser:
python manage.py createsuperuser

7. Run the development server
python manage.py runserver
The API will be available at http://127.0.0.1:8000/.

📖 API Documentation & Endpoints
Once the server is running, explore and test the endpoints via interactive docs:
Swagger UI: http://127.0.0.1:8000/api/doc/swagger/
Redoc: http://127.0.0.1:8000/api/doc/redoc/

💳 Stripe Testing Credentials
To test payments in Stripe Checkout test mode:
Card Number: 4242 4242 4242 4242
Expiration Date: Any valid future date (e.g. 12/28)
CVC: Any 3 digits (e.g. 123)
ZIP / Postal code: Any valid zip code

🧪 Testing & Code Coverage
Run the test suite with coverage report:
coverage run manage.py test
coverage report
To generate an interactive HTML coverage report:
coverage html
# Open htmlcov/index.html in your browser
