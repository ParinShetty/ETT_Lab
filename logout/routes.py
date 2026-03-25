from flask import Blueprint, redirect, url_for, session

logout_bp= Blueprint('logout',__name__)
@logout_bp.route("/")
def logout():
    session.pop("user", None)
    return redirect(url_for("main.index"))
