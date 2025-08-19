# index.py
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import os
import time
import base64
import traceback
import firebase_admin
from firebase_admin import credentials, db
import stripe
import json

# ---- Paths ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# ---- Flask ----
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
# Allow file:// page or any origin to call this API:
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# ---- Firebase Admin ----
# Initialize Firebase Admin SDK
firebase_initialized = False
try:
    cred = credentials.Certificate("serviceAccountKey.json")  # You'll need to add your service account key
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://perseptra-default-rtdb.firebaseio.com'
    })
    firebase_initialized = True
    print("Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"Firebase Admin initialization failed: {e}")
    print("Using local storage fallback for testing")
    # Continue without Firebase for now

# ---- Stripe Configuration ----
# Initialize Stripe with your secret key
stripe.api_key = 'sk_test_YOUR_STRIPE_SECRET_KEY'  # Replace with your actual Stripe secret key
STRIPE_WEBHOOK_SECRET = 'whsec_YOUR_WEBHOOK_SECRET'  # Replace with your webhook secret

# Plan configurations
STRIPE_PLANS = {
    'price_starter': {
        'credits': 200,
        'name': 'Starter Plan'
    },
    'price_pro': {
        'credits': 1000,
        'name': 'Pro Plan'
    },
    'price_enterprise': {
        'credits': 3000,
        'name': 'Enterprise Plan'
    }
}

# ---- Vertex AI (your settings) ----
vertexai.init(project="perseptra-468600", location="us-central1")
model = ImageGenerationModel.from_pretrained("imagen-4.0-generate-preview-06-06")

def _extract_first_image_bytes(gen_result):
    """Be tolerant of SDK return shapes and attributes."""
    # gen_result can be a list or an object with .images
    imgs = gen_result.images if hasattr(gen_result, "images") else gen_result
    if not imgs:
        raise RuntimeError("No images returned from Vertex AI")

    img = imgs[0]

    # Try common attributes
    for attr in ("_image_bytes", "image_bytes", "bytes", "data"):
        b = getattr(img, attr, None)
        if b:
            if isinstance(b, str):
                # some SDKs send base64 strings
                try:
                    return base64.b64decode(b)
                except Exception:
                    pass
            return b

    # Try base64 hints
    for attr in ("_image_b64", "image_b64", "b64"):
        b64 = getattr(img, attr, None)
        if b64:
            return base64.b64decode(b64)

    raise RuntimeError("Could not extract image bytes from model response")

def check_and_deduct_credits(user_id, cost=1):
    """Check if user has enough credits and deduct them"""
    if not firebase_initialized:
        # Fallback for testing - use simple file storage
        import json
        import os
        
        credits_file = "user_credits.json"
        
        # Load existing credits
        if os.path.exists(credits_file):
            with open(credits_file, 'r') as f:
                credits_data = json.load(f)
        else:
            credits_data = {}
        
        current_credits = credits_data.get(user_id, 0)
        
        if current_credits < cost:
            return False, current_credits
        
        # Deduct credits
        new_balance = current_credits - cost
        credits_data[user_id] = new_balance
        
        # Save back to file
        with open(credits_file, 'w') as f:
            json.dump(credits_data, f, indent=2)
        
        print(f"Credits deducted for user {user_id}: {cost} credits. New balance: {new_balance}")
        return True, new_balance
    
    try:
        # Get current credits
        ref = db.reference(f'credits/{user_id}')
        snapshot = ref.get()
        
        if snapshot is None:
            # User doesn't exist, create with 0 credits
            ref.set({'balance': 0})
            return False, 0
        
        current_credits = snapshot.get('balance', 0)
        
        if current_credits < cost:
            return False, current_credits
        
        # Deduct credits
        new_balance = current_credits - cost
        ref.update({'balance': new_balance})
        
        return True, new_balance
        
    except Exception as e:
        print(f"Error checking/deducting credits: {e}")
        return False, 0

def add_credits_to_user(user_id, amount):
    """Add credits to a user's account"""
    if not firebase_initialized:
        # Fallback for testing - use simple file storage
        import json
        import os
        
        credits_file = "user_credits.json"
        
        # Load existing credits
        if os.path.exists(credits_file):
            with open(credits_file, 'r') as f:
                credits_data = json.load(f)
        else:
            credits_data = {}
        
        current_credits = credits_data.get(user_id, 0)
        new_balance = current_credits + amount
        credits_data[user_id] = new_balance
        
        # Save back to file
        with open(credits_file, 'w') as f:
            json.dump(credits_data, f, indent=2)
        
        print(f"Credits added for user {user_id}: {amount} credits. New balance: {new_balance}")
        return new_balance
    
    try:
        ref = db.reference(f'credits/{user_id}')
        snapshot = ref.get()
        
        if snapshot is None:
            # User doesn't exist, create with the amount
            ref.set({'balance': amount})
            return amount
        else:
            # Add to existing balance
            current_credits = snapshot.get('balance', 0)
            new_balance = current_credits + amount
            ref.update({'balance': new_balance})
            return new_balance
            
    except Exception as e:
        print(f"Error adding credits: {e}")
        return 0

@app.route("/", methods=["GET"])
def root():
    """Simple root route to confirm deployment on Render"""
    return "Flask API is running on Render!"

@app.route("/html", methods=["GET"])
def serve_html():
    # Serve image.html from the SAME folder as index.py
    return send_from_directory(BASE_DIR, "image.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "firebase_initialized": firebase_initialized})

@app.route("/test-claim", methods=["GET"])
def test_claim():
    """Simple test endpoint for daily credits"""
    return jsonify({
        "success": True,
        "creditsAdded": 15,
        "newBalance": 100,
        "message": "Test claim successful!"
    })

@app.route("/claim-daily-credits", methods=["GET"])
def claim_daily_credits_get():
    """GET version for testing"""
    return jsonify({
        "success": True,
        "creditsAdded": 15,
        "newBalance": 100,
        "message": "Daily credits claimed successfully! (GET Test)"
    })

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        user_id = data.get("userId")
        
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400

        # Check and deduct credits
        success, remaining_credits = check_and_deduct_credits(user_id, cost=1)
        if not success:
            return jsonify({
                "error": "Insufficient credits. You need 1 credit to generate an image.",
                "currentCredits": remaining_credits
            }), 402

        # IMPORTANT: Imagen 4.0 does NOT take a `size` argument.
        res = model.generate_images(prompt=prompt, number_of_images=1)

        img_bytes = _extract_first_image_bytes(res)

        # Unique filename (ns timestamp)
        filename = f"generated_{time.time_ns()}.png"
        filepath = os.path.join(STATIC_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(img_bytes)

        # Absolute URL (works even if image.html is opened via file://)
        absolute_url = request.host_url.rstrip("/") + url_for("static", filename=filename)

        return jsonify({
            "filename": filename,
            "relative_url": f"/static/{filename}",
            "url": absolute_url,
            "remainingCredits": remaining_credits
        })

    except Exception as e:
        print("\n--- ERROR in /generate ---")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/generate-video", methods=["POST"])
def generate_video():
    try:
        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        duration = data.get("duration", 10)
        quality = data.get("quality", "hd")
        user_id = data.get("userId")
        
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400

        # Check and deduct credits (video costs 25 credits)
        success, remaining_credits = check_and_deduct_credits(user_id, cost=25)
        if not success:
            return jsonify({
                "error": "Insufficient credits. You need 25 credits to generate a video.",
                "currentCredits": remaining_credits
            }), 402

        # For now, simulate video generation with a placeholder
        # In a real implementation, you would use a video generation API like Runway ML, Pika Labs, etc.
        
        # Create a placeholder video file (this is just for demonstration)
        # In production, you would integrate with actual video generation services
        
        # Unique filename (ns timestamp)
        filename = f"generated_video_{time.time_ns()}.mp4"
        filepath = os.path.join(STATIC_DIR, filename)
        
        # Create a simple placeholder video file (this is just for demo purposes)
        # In reality, you would call a video generation API here
        with open(filepath, "wb") as f:
            # Write a minimal MP4 header (this is just a placeholder)
            f.write(b'\x00\x00\x00\x20ftypmp42')
        
        # Absolute URL
        absolute_url = request.host_url.rstrip("/") + url_for("static", filename=filename)

        return jsonify({
            "filename": filename,
            "relative_url": f"/static/{filename}",
            "url": absolute_url,
            "remainingCredits": remaining_credits,
            "duration": duration,
            "quality": quality
        })

    except Exception as e:
        print("\n--- ERROR in /generate-video ---")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/add-credits", methods=["POST"])
def add_credits():
    """Add credits to a user (for testing purposes)"""
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get("userId")
        amount = data.get("amount", 100)  # Default 100 credits
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        new_balance = add_credits_to_user(user_id, amount)
        
        return jsonify({
            "success": True,
            "creditsAdded": amount,
            "newBalance": new_balance
        })
        
    except Exception as e:
        print(f"Error adding credits: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/get-credits/<user_id>", methods=["GET"])
def get_credits(user_id):
    """Get current credit balance for a user"""
    try:
        if not firebase_initialized:
            # Fallback for testing - use simple file storage
            import json
            import os
            from datetime import datetime
            
            credits_file = "user_credits.json"
            claims_file = "daily_claims.json"
            
            # Load existing credits
            if os.path.exists(credits_file):
                with open(credits_file, 'r') as f:
                    credits_data = json.load(f)
            else:
                credits_data = {}
            
            # Load daily claims
            if os.path.exists(claims_file):
                with open(claims_file, 'r') as f:
                    claims_data = json.load(f)
            else:
                claims_data = {}
            
            balance = credits_data.get(user_id, 0)
            last_claim_date = claims_data.get(user_id)
            
            # Check if user can claim daily credits
            today = datetime.now().strftime("%Y-%m-%d")
            can_claim_daily = last_claim_date != today
            
            print(f"User {user_id} balance: {balance}, can claim daily: {can_claim_daily}")
            
            return jsonify({
                "balance": balance,
                "canClaimDaily": can_claim_daily,
                "lastClaimDate": last_claim_date
            })
        
        ref = db.reference(f'credits/{user_id}')
        snapshot = ref.get()
        
        if snapshot is None:
            return jsonify({"balance": 0, "canClaimDaily": True})
        
        balance = snapshot.get('balance', 0)
        last_claim_date = snapshot.get('lastClaimDate')
        
        # Check if user can claim daily credits
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        can_claim_daily = last_claim_date != today
        
        return jsonify({
            "balance": balance,
            "canClaimDaily": can_claim_daily,
            "lastClaimDate": last_claim_date
        })
        
    except Exception as e:
        print(f"Error getting credits: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/claim-daily-credits", methods=["POST"])
def claim_daily_credits():
    """Claim daily free credits (15 credits per day)"""
    try:
        print("Claim daily credits endpoint called")
        data = request.get_json(silent=True) or {}
        print("Request data:", data)
        user_id = data.get("userId")
        
        if not user_id:
            print("No user ID provided")
            return jsonify({"error": "User ID required"}), 400
        
        print(f"Processing claim for user: {user_id}")
        
        if not firebase_initialized:
            # Fallback for testing - use simple file storage
            import json
            import os
            from datetime import datetime
            
            credits_file = "user_credits.json"
            claims_file = "daily_claims.json"
            
            # Load existing credits
            if os.path.exists(credits_file):
                with open(credits_file, 'r') as f:
                    credits_data = json.load(f)
            else:
                credits_data = {}
            
            # Load daily claims
            if os.path.exists(claims_file):
                with open(claims_file, 'r') as f:
                    claims_data = json.load(f)
            else:
                claims_data = {}
            
            # Check if user has already claimed today
            today = datetime.now().strftime("%Y-%m-%d")
            last_claim_date = claims_data.get(user_id)
            
            if last_claim_date == today:
                current_balance = credits_data.get(user_id, 0)
                return jsonify({
                    "error": "You have already claimed your daily credits today. Come back tomorrow!",
                    "currentBalance": current_balance
                }), 400
            
            # Add daily credits
            current_balance = credits_data.get(user_id, 0)
            new_balance = current_balance + 15
            credits_data[user_id] = new_balance
            claims_data[user_id] = today
            
            # Save back to files
            with open(credits_file, 'w') as f:
                json.dump(credits_data, f, indent=2)
            with open(claims_file, 'w') as f:
                json.dump(claims_data, f, indent=2)
            
            print(f"Daily credits claimed for user {user_id}: +15 credits. New balance: {new_balance}")
            
            response_data = {
                "success": True,
                "creditsAdded": 15,
                "newBalance": new_balance,
                "message": "Daily credits claimed successfully! (File Mode)"
            }
            print("Returning response:", response_data)
            return jsonify(response_data)
        
        # Get current date in YYYY-MM-DD format
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check if user has already claimed today
        ref = db.reference(f'credits/{user_id}')
        snapshot = ref.get()
        
        if snapshot is None:
            # User doesn't exist, create with daily credits
            ref.set({
                'balance': 15,
                'lastClaimDate': today
            })
            return jsonify({
                "success": True,
                "creditsAdded": 15,
                "newBalance": 15,
                "message": "Daily credits claimed successfully!"
            })
        
        last_claim_date = snapshot.get('lastClaimDate')
        current_balance = snapshot.get('balance', 0)
        
        if last_claim_date == today:
            return jsonify({
                "error": "You have already claimed your daily credits today. Come back tomorrow!",
                "currentBalance": current_balance
            }), 400
        
        # Add daily credits
        new_balance = current_balance + 15
        ref.update({
            'balance': new_balance,
            'lastClaimDate': today
        })
        
        return jsonify({
            "success": True,
            "creditsAdded": 15,
            "newBalance": new_balance,
            "message": "Daily credits claimed successfully!"
        })
        
    except Exception as e:
        print(f"Error claiming daily credits: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Create a Stripe checkout session with user metadata"""
    try:
        data = request.get_json()
        plan = data.get('plan')
        user_id = data.get('userId')
        
        if not plan or not user_id:
            return jsonify({"error": "Missing plan or userId"}), 400
        
        # Map plan names to Stripe price IDs
        plan_to_price = {
            'starter': 'price_starter',  # Replace with your actual Stripe price ID
            'pro': 'price_pro',          # Replace with your actual Stripe price ID
            'enterprise': 'price_enterprise'  # Replace with your actual Stripe price ID
        }
        
        price_id = plan_to_price.get(plan)
        if not price_id:
            return jsonify({"error": "Invalid plan"}), 400
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://127.0.0.1:5000/pricing.html?success=true',
            cancel_url='http://127.0.0.1:5000/pricing.html?canceled=true',
            metadata={
                'user_id': user_id,
                'plan': plan
            }
        )
        
        return jsonify({
            "success": True,
            "url": checkout_session.url
        })
        
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events for successful payments"""
    try:
        # Get the webhook payload
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        if not sig_header:
            print("No Stripe signature found")
            return jsonify({"error": "No signature"}), 400
        
        try:
            # Verify the webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            print(f"Invalid payload: {e}")
            return jsonify({"error": "Invalid payload"}), 400
        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {e}")
            return jsonify({"error": "Invalid signature"}), 400
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Extract user ID from metadata
            user_id = session.get('metadata', {}).get('user_id')
            if not user_id:
                print("No user_id found in session metadata")
                return jsonify({"error": "No user_id"}), 400
            
            # Determine which plan was purchased
            line_items = stripe.checkout.Session.list_line_items(session['id'])
            if not line_items.data:
                print("No line items found in session")
                return jsonify({"error": "No line items"}), 400
            
            # Get the price ID from the first line item
            price_id = line_items.data[0].price.id
            
            # Find the plan configuration
            plan_config = None
            for plan_id, config in STRIPE_PLANS.items():
                if plan_id == price_id:
                    plan_config = config
                    break
            
            if not plan_config:
                print(f"Unknown price ID: {price_id}")
                return jsonify({"error": "Unknown plan"}), 400
            
            # Add credits to user's account
            credits_to_add = plan_config['credits']
            new_balance = add_credits_to_user(user_id, credits_to_add)
            
            print(f"Payment successful! Added {credits_to_add} credits to user {user_id}. New balance: {new_balance}")
            
            return jsonify({
                "success": True,
                "message": f"Added {credits_to_add} credits to user {user_id}",
                "new_balance": new_balance
            })
        
        elif event['type'] == 'payment_intent.succeeded':
            print("Payment intent succeeded")
            return jsonify({"success": True})
        
        else:
            print(f"Unhandled event type: {event['type']}")
            return jsonify({"success": True})
            
    except Exception as e:
        print(f"Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
