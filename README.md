# Smart Medicine Reminder & Expiry Tracker — Web Version

This is a browser-based adaptation of the supplied Tkinter desktop project, built with Streamlit and SQLite.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run: `pip install -r requirements.txt`
4. Run: `streamlit run app.py`
5. Open the local URL shown in the terminal (usually http://localhost:8501).

## Deploy on Render
1. Create a GitHub account and upload the contents of this folder to a new repository.
2. In Render, choose **New + → Web Service** and connect that repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Choose a persistent disk mounted at `/opt/render/project/src/data` if you want SQLite data to survive restarts/deploys. Without persistent storage, the database may be reset.

## Notes
- This web version recreates the main project functions: accounts, medicine records, reminders list, taken/missed history, expiry/stock alerts, CSV export and basic analytics.
- The original desktop Tkinter application is included separately in the original ZIP; this web version is a browser adaptation, not a one-click conversion of Tkinter.
- Browser reminder list is visible when the page is open; it does not send background notifications when the browser is closed.
- This is an educational project, not medical advice.


## Updated blue interface
This package now uses a navy-blue sidebar, light-blue page background, white dashboard cards, blue action buttons, and matching login/register styling. Existing application logic and database features are retained.

## Publish the blue version
Replace the files in the GitHub repository connected to your Render service with the contents of this folder, commit the changes, and wait for Render to redeploy. The existing Render URL can stay the same. If you use a persistent disk for the SQLite database, keep its mount path unchanged.
