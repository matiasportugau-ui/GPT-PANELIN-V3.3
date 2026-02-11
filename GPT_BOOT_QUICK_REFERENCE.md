# GPT Auto-Boot Quick Reference Card

**Version**: 1.0 | **Date**: 2026-02-11 | **Repository**: matiasportugau-ui/GPT-PANELIN-V3.2

---

## 🚀 Quick Deployment (60 seconds)

### Step 1: Open GPT Builder
Go to: https://chat.openai.com/gpts/editor

### Step 2: Add Boot Directive
Copy `GPT_BOOT_INSTRUCTIONS_COMPACT.md` and paste at the **TOP** of the Instructions field

### Step 3: Save & Test
Save GPT → Start new conversation → Verify boot executes automatically

---

## 📋 What the Boot Does

✅ Scans all uploaded knowledge files  
✅ Generates structured index table  
✅ Shows operational log (4 phases)  
✅ Displays readiness confirmation  
✅ Provides conversation starters  
✅ Hides internal reasoning (security)  

---

## 📊 Expected Output

```
🔄 PANELIN BOOT SEQUENCE - Initializing Knowledge Base
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ PHASE 1: Knowledge Base Scan
   → Files detected: 17 files across 5 categories
   → Status: ✅ COMPLETE

[... Phases 2-4 ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ BOOT COMPLETE - All systems operational
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 KNOWLEDGE BASE INDEX
[... Index table with all files ...]

✅ SYSTEM READY - Panelin 3.3 (BMC Assistant Pro)
[... Conversation starters ...]
```

---

## 🐛 Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Boot doesn't run | Move boot directive to very top of instructions |
| Index table empty | Wait 2-3 min after upload, start new conversation |
| Internal logs visible | Add "DO NOT show internal reasoning" to instructions |
| Boot too slow | Simplify table format, reduce phases to 2 |

---

## 📁 File Structure

**Created Files**:
1. `GPT_SYSTEM_PROMPT_AUTOBOOT.md` - Complete specification (reference)
2. `GPT_BOOT_INSTRUCTIONS_COMPACT.md` - Ready-to-use directive (deploy this)
3. `GPT_BOOT_IMPLEMENTATION_GUIDE.md` - Detailed deployment guide
4. `GPT_BOOT_QUICK_REFERENCE.md` - This quick reference card

**Usage**:
- **Deploy**: Use #2 (compact instructions)
- **Learn**: Read #3 (implementation guide)
- **Reference**: Consult #1 (full specification)
- **Quick checks**: Use #4 (this card)

---

## ✅ Success Checklist

- [ ] Boot runs automatically at session start
- [ ] All 17 files appear in index table
- [ ] No debug info visible to users
- [ ] Conversation starters work correctly
- [ ] Users can query files by name

---

## 📚 Key Concepts

**Boot Process**: Automatic file scanning and indexing at session start  
**Index Table**: Structured list of all knowledge files with metadata  
**Operational Log**: User-visible boot phases (scan → index → validate → ready)  
**Security**: Hide internal reasoning, show only operational output  
**Queryability**: Users can reference indexed files by name during conversation  

---

## 🎯 Integration Points

**With Panelin Instructions**: Boot runs first, then Panelin instructions apply  
**With KB Hierarchy**: Boot respects Level 1-4 structure from PANELIN_KNOWLEDGE_BASE_GUIDE.md  
**With Upload Process**: Boot scans files uploaded via GPT_UPLOAD_CHECKLIST.md  
**With PDF Generation**: Boot confirms bmc_logo.png availability for PDF gen  

---

## 🔧 Customization Quick Tips

**Faster boot**: Reduce to 2 phases, simplify table  
**More detail**: Add file sizes, descriptions  
**Different project**: Update file list, conversation starters  
**Hide index**: Move to `/show_index` command instead of auto-display  

---

## 📞 Need More Info?

- **Detailed steps**: See `GPT_BOOT_IMPLEMENTATION_GUIDE.md`
- **Full specification**: See `GPT_SYSTEM_PROMPT_AUTOBOOT.md`
- **Deployment instructions**: See `GPT_BOOT_INSTRUCTIONS_COMPACT.md`

---

## 💡 Pro Tips

✨ Test boot in a new conversation (not existing one)  
✨ Wait 2-3 min after uploading files before testing  
✨ Use "CRITICAL: Execute automatically" for reliable boot  
✨ Keep index in working memory for user queries  
✨ Update index table when files change  

---

**Quick Deploy**: Copy `GPT_BOOT_INSTRUCTIONS_COMPACT.md` → Paste at top of GPT instructions → Save → Test

**That's it! Boot should now run automatically at every session start.**
