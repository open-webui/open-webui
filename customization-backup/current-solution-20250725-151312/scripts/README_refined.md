# mAI Client API Key Generator - Refined Version

## 🎯 **Quick Start**

```bash
# Basic usage with default $1000 limit
python3 scripts/mai_keygen.py "Polish Company ABC"

# Custom spending limit
python3 scripts/mai_keygen.py "Warsaw Tech Ltd" --limit 500

# Unlimited spending
python3 scripts/mai_keygen.py "Enterprise Corp" --limit unlimited

# JSON output format
python3 scripts/mai_keygen.py "Startup XYZ" --format json

# No file output (display only)
python3 scripts/mai_keygen.py "Test Client" --no-file
```

## 📋 **Script Features**

### ✅ **Flexible Organization Names**
- **Validation**: 2-100 characters
- **Automatic cleaning**: Removes invalid characters  
- **Smart labeling**: Generates clean OpenRouter labels

### ✅ **Spending Limit Options**
- **Numbers**: `500`, `1000`, `2500.50`
- **Unlimited**: `unlimited`, `none`, `infinite`, `0`
- **Currency**: Strips `$`, `€`, `£` symbols automatically
- **Default**: $1000 if not specified

### ✅ **Output Formats**
- **TXT** (default): Human-readable with instructions
- **JSON**: Machine-readable with structured data
- **No file**: Display results only (with `--no-file`)

### ✅ **Enhanced Error Handling**
- Input validation with clear error messages
- Network error handling and retries
- Malformed response detection
- User-friendly error descriptions

## 🚀 **Usage Examples**

### **Standard Client Setup**
```bash
python3 scripts/mai_keygen.py "Kraków Digital Solutions" --limit 750
```

**Output**:
- API key generated with $750/month limit
- Client instructions in text file
- Ready to send to client

### **Enterprise Client (Unlimited)**
```bash
python3 scripts/mai_keygen.py "Enterprise Corporation" --limit unlimited --format json
```

**Output**:
- API key with no spending limits
- JSON format for automation
- Structured data for integration

### **Startup Client (Low Limit)**
```bash
python3 scripts/mai_keygen.py "Startup Poland" --limit 100
```

**Output**:
- API key with $100/month limit
- Perfect for testing/small clients
- Full tracking capabilities

## 📁 **Generated Files**

### **Text Format** (default)
```
api_key_Warsaw_Tech_Solutions_20250725_135558.txt
```

Contains:
- Organization details
- Complete API key  
- Setup instructions for client
- Technical details (hash, creation date)
- Notes about automatic mapping

### **JSON Format** (with `--format json`)
```json
{
  "organization_name": "Warsaw Tech Solutions",
  "api_key": "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",
  "key_hash": "ebf46431e3b001e11796968df011a70f651b12f73cac13dacf23f477f4699f0b",
  "spending_limit": 500.0,
  "created_at": "2025-07-25T11:55:58.046739+00:00",
  "instructions": {
    "step_1": "Give API key to client",
    "step_2": "Client opens mAI → Settings → Connections",
    "step_3": "Client adds OpenRouter connection",
    "step_4": "URL: https://openrouter.ai/api/v1",
    "step_5": "API Key: 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",
    "step_6": "Client clicks Save",
    "step_7": "Automatic mapping activates"
  }
}
```

## 🎯 **Client Workflow**

### **Step 1: Generate API Key (You)**
```bash
python3 scripts/mai_keygen.py "Client Name" --limit 1000
```

### **Step 2: Send to Client (You → Client)**
- Email the generated API key
- Include setup instructions from the file
- Or send the entire `.txt` file

### **Step 3: Client Setup (Client)**
1. Open mAI → **Settings → Connections**
2. Add OpenRouter connection:
   - **URL**: `https://openrouter.ai/api/v1`
   - **API Key**: `sk-or-v1-...` (from file)
3. Click **Save**

### **Step 4: Automatic (System)**
- ✅ Organization created automatically
- ✅ User mapped to organization  
- ✅ Usage tracking starts with 1.3x markup
- ✅ Real-time monitoring active

## 🔧 **Advanced Options**

### **Help and Documentation**
```bash
python3 scripts/mai_keygen.py --help
```

### **Validation Examples**
```bash
# Too short name (fails)
python3 scripts/mai_keygen.py "A"

# Invalid limit format (fails)  
python3 scripts/mai_keygen.py "Client" --limit "invalid"

# Valid alternatives for unlimited
python3 scripts/mai_keygen.py "Client" --limit none
python3 scripts/mai_keygen.py "Client" --limit unlimited
python3 scripts/mai_keygen.py "Client" --limit 0
```

### **Currency Handling**
```bash
# All equivalent to $500 limit
python3 scripts/mai_keygen.py "Client" --limit 500
python3 scripts/mai_keygen.py "Client" --limit $500
python3 scripts/mai_keygen.py "Client" --limit "500.00"
python3 scripts/mai_keygen.py "Client" --limit "€500"
```

## 🎉 **Production Ready**

**The refined script is ready for your 20+ Polish client deployment:**

- ✅ **Robust error handling** for production use
- ✅ **Flexible input validation** for different client needs
- ✅ **Professional output formats** for client communication
- ✅ **Automatic file naming** with timestamps
- ✅ **Complete integration** with mAI automatic mapping
- ✅ **Spending limit flexibility** from $10 to unlimited
- ✅ **Clear instructions** for non-technical clients

**Your mAI key generation system is now enterprise-ready!** 🚀