#!/usr/bin/env python3
"""
Test Automatic API Key Mapping
"""

print("🧪 TESTING AUTOMATIC API KEY MAPPING")
print("=" * 50)

test_api_key = "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"

print("🎯 When config is saved via UI, it should trigger:")
print("   1. ✅ Detect OpenRouter URL + API key")
print("   2. ✅ Call sync_ui_key_to_organization()")
print("   3. ✅ Create organization automatically") 
print("   4. ✅ Map user to organization")
print("   5. ✅ Set 1.3x markup rate")

print("\n🔄 To test: Go to Settings → Connections and click Save again")
print(f"   API Key: {test_api_key[:20]}...{test_api_key[-10:]}")