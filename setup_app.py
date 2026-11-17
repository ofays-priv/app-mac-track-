from setuptools import setup

APP = ["deviation_tracker/app.py"]
DATA_FILES = ["examples/config.example.json"]
OPTIONS = {
    "py2app": {
        "plist": {
            "CFBundleName": "DeviationTracker",
            "CFBundleDisplayName": "Deviations",
            "CFBundleIdentifier": "fr.entreprise.deviationtracker",
            "LSUIElement": True,
            "NSAppleEventsUsageDescription": "Integration avec Mail.app pour joindre les e-mails sources et envoyer le resume.",
        }
    }
}

setup(
    name="DeviationTracker",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
