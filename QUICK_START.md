# Quick Deployment Guide for Friends

## TL;DR - Fastest Way to Share

**Option 1: Streamlit Cloud (5 minutes, Free)**

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and deploy
4. Add your OpenAI API key in secrets
5. Share the URL with your friend!

---

## For Your Friend to Use Their Own PDFs

Your friend can now:
1. Visit the deployed URL
2. Click "Upload PDFs" in the sidebar
3. Select their PDF files
4. Click "Process Uploaded Files"
5. Use the study tools with their content!

### Important Notes:

**API Key Usage:**
- When you deploy with YOUR API key, all usage (by you and your friend) will be charged to YOUR OpenAI account
- This is fine for personal use, but monitor your costs at https://platform.openai.com/usage

**Better Approach for Multiple Users:**
- Ask your friend to get their own OpenAI API key (free tier available)
- They can run the app locally with their key, OR
- You can modify the app to let users input their own API key

### Let Users Provide Their Own API Key

Add this to the top of `app_enhanced.py`:

```python
# In sidebar, before file upload
with st.sidebar:
    st.header("🔑 API Configuration")
    user_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Get your key at https://platform.openai.com/api-keys"
    )
    
    if user_api_key:
        os.environ["OPENAI_API_KEY"] = user_api_key
        st.success("API key configured!")
    elif not os.getenv("OPENAI_API_KEY"):
        st.warning("Please enter your OpenAI API key to use the app")
        st.stop()
```

## Cost Estimate

### If using YOUR API key for a friend:

- Processing 20 PDFs (~200 pages): $2-5
- 50 questions/queries per week: $5-10/week
- Monthly cost for 1 active friend: $20-40

### Recommendation:
- For 1-2 friends: Share your deployment with your API key
- For more users: Have them use their own keys or set up payment

## Privacy Considerations

### User Data Isolation:
The app creates separate databases for each user session:
```
db_abc123/  # User 1's data
db_def456/  # User 2's data
```

### Data Persistence:
- On Streamlit Cloud: Data resets when app restarts
- On Railway/Render: Data persists until you clear it
- For permanent storage: Add cloud storage (S3, GCS)

### To Clear All User Data:
```bash
# Delete all user databases
rm -rf db_*
```

## Deployment Comparison

| Platform | Cost | Setup Time | Best For |
|----------|------|------------|----------|
| **Streamlit Cloud** | Free (with limits) | 5 min | Quick sharing, demos |
| **Railway** | $5-10/mo | 10 min | Small groups, reliable |
| **Render** | Free (slow) or $7/mo | 10 min | Budget-conscious |
| **Self-hosted** | $5-20/mo | 1 hour | Full control, many users |

## Example: Deploy to Streamlit Cloud

### Step-by-step:

1. **Prepare GitHub repo:**
```bash
cd "/Users/gigihsu/Documents/SCHOOL/Fall 2025/Intro to AI/1710-hw7-ggshoo"
git add .
git commit -m "Add deployment files"
git push origin main
```

2. **Deploy:**
   - Visit https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Repository: `cpsc1710-fa25/1710-hw7-ggshoo`
   - Branch: `main`
   - Main file: `app_enhanced.py`
   - Click "Deploy!"

3. **Add API Key:**
   - Go to app settings (⋮ menu)
   - Click "Secrets"
   - Add:
     ```toml
     OPENAI_API_KEY = "sk-your-actual-key-here"
     ```
   - Save

4. **Share:**
   - Copy the URL (e.g., `https://your-username-ai-study.streamlit.app`)
   - Send to your friend with instructions

## Instructions to Send Your Friend

```
Hi! I built a study assistant that can help you with your course materials.

📱 Access: [YOUR-APP-URL]

🎯 How to use:
1. Click "Upload PDFs" in the sidebar
2. Select your lecture notes or textbook PDFs
3. Click "Process Uploaded Files" and wait
4. Use the study tools:
   - Ask Questions: Get answers from your materials
   - Generate Quiz: Create practice tests
   - Create Study Guide: Get organized summaries
   - Concept Map: Visualize relationships

💡 Tips:
- Upload all your materials at once for best results
- Ask specific questions for better answers
- Try different topics for quizzes and guides

⚠️ Note: Processing large files may take a minute. Be patient!

Any issues? Let me know!
```

## Monitoring Usage

### Check OpenAI Costs:
1. Visit https://platform.openai.com/usage
2. View daily/monthly usage
3. Set up billing alerts

### Streamlit Analytics:
- View app metrics in Streamlit Cloud dashboard
- See number of visitors
- Check resource usage

## Troubleshooting

### "App is starting..."
- First load takes ~30 seconds
- Free tier apps sleep after 7 days of inactivity

### "Error processing PDF"
- File might be too large (>10MB)
- PDF might be scanned image (needs OCR)
- Try smaller files first

### "Rate limit exceeded"
- Too many requests too quickly
- Wait a minute and try again
- Consider adding rate limiting (see DEPLOYMENT.md)

## Next Steps

1. Deploy to Streamlit Cloud (easiest)
2. Test with your friend
3. If usage grows, consider:
   - Upgrading to paid tier
   - Adding authentication
   - Having users provide their own API keys
   - Self-hosting for more control

Need help? Check the full DEPLOYMENT.md guide!