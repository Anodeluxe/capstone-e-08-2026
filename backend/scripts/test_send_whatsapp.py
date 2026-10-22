"""
Test script to send WhatsApp notifications via WAHA or Fonnte.
Usage:
    python backend/scripts/test_send_whatsapp.py --target 081319260286 --type test
    python backend/scripts/test_send_whatsapp.py --target 081319260286 --type valve
    python backend/scripts/test_send_whatsapp.py --target 081319260286 --type sudden
    python backend/scripts/test_send_whatsapp.py --target 081319260286 --type ews
"""

import argparse
import asyncio
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path so app imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services import notification_service


async def main():
    parser = argparse.ArgumentParser(description="Test WhatsApp notification dispatch")
    parser.add_argument("--target", default="081319260286", help="Target WhatsApp phone number")
    parser.add_argument(
        "--type",
        choices=["test", "valve", "sudden", "ews"],
        default="test",
        help="Type of notification alert to send",
    )
    args = parser.parse_args()

    settings = get_settings()
    chat_id = notification_service.format_waha_chat_id(args.target)

    print("==================================================")
    print("      TOREN WATER MONITORING — WA NOTIFICATION     ")
    print("==================================================")
    print(f"Provider     : {settings.whatsapp_provider}")
    print(f"WAHA Base URL: {settings.waha_base_url}")
    print(f"Session      : {settings.waha_session}")
    print(f"Target Input : {args.target}")
    print(f"Formatted ID : {chat_id}")
    print(f"Alert Type   : {args.type.upper()}")
    print("--------------------------------------------------")

    # Step 1: Check session status if using WAHA
    if settings.whatsapp_provider == "waha":
        print(f"Checking WAHA status at {settings.waha_base_url}...")
        status_info = await notification_service.check_waha_session_status()
        print(f"WAHA Status  : {status_info.get('status')}")

        if not status_info.get("online"):
            print("\n❌ WAHA container is not reachable!")
            print(f"   Error: {status_info.get('error') or status_info.get('message')}")
            print("\n   👉 Please start WAHA:")
            print("   1. Open Docker Desktop.")
            print("   2. Run: docker compose up -d waha")
            print("   3. Open http://localhost:3008/dashboard and scan the QR code.")
            return

        session_state = status_info.get("details", {}).get("status") or status_info.get("status")
        if session_state != "WORKING":
            print(f"\n⚠️  WAHA session '{settings.waha_session}' status is: {session_state}")
            print("   Please scan the QR code to pair your WhatsApp account:")
            print("   👉 Open: http://localhost:3008/dashboard")
            return

        print("✅ WAHA is online and WhatsApp session is CONNECTED (WORKING).")

    # Step 2: Build and dispatch message
    print("\nDispatching message...")
    # Override settings targets temporarily for this test
    original_targets = settings.notif_whatsapp_targets
    settings.notif_whatsapp_targets = args.target

    try:
        if args.type == "test":
            text = (
                f"🔔 *UJI COBA NOTIFIKASI CAPSTONE E-08*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Halo! Ini adalah pesan uji coba dari *Sistem Monitoring Kualitas Air Toren* (DTETI FT UGM).\n\n"
                f"• *Kanal:* WhatsApp (WAHA Gateway)\n"
                f"• *Target:* `{args.target}`\n"
                f"• *Status:* Berhasil Terhubung! ✅\n\n"
                f"_— Tim Capstone DTETI UGM 2026_"
            )
            success = await notification_service._send_whatsapp(text)
        elif args.type == "valve":
            results = await notification_service.send_valve_closed_notification(
                valve_id="bathroom",
                score=42.5,
                anomaly_param="turbidity",
            )
            success = results.get("whatsapp", False)
        elif args.type == "sudden":
            results = await notification_service.send_sudden_change_notification(
                parameter="turbidity",
                current_value=48.2,
                previous_value=2.1,
                current_score=35.0,
            )
            success = results.get("whatsapp", False)
        elif args.type == "ews":
            results = await notification_service.send_early_warning_notification(
                days_until=3.5,
                predicted_date="18 Oct 2026",
                current_score=58.0,
                valve_id="bathroom",
            )
            success = results.get("whatsapp", False)
        else:
            success = False

        if success:
            print(f"🎉 SUCCESS! WhatsApp message sent to {args.target} ({chat_id})")
        else:
            print(f"❌ FAILED to send WhatsApp message to {args.target}. Check logs above.")

    finally:
        settings.notif_whatsapp_targets = original_targets


if __name__ == "__main__":
    asyncio.run(main())
