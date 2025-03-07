# Copyright 2017 the Isard-vdi project authors:
#      Josep Maria Viñolas Auquer
#      Alberto Larraz Dalmases
# License: AGPLv3

#!flask/bin/python
# coding=utf-8
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from webapp import app

# ~ from ..auth.authentication import *
from ..lib.log import *


@app.route("/isard-admin/profile", methods=["POST", "GET"])
@login_required
def profile():
    if request.method == "POST":
        None
    user = app.isardapi.get_user(current_user.id)
    return render_template("pages/user_profile.html", user=user)


@app.route("/isard-admin/profile_pwd", methods=["POST"])
@login_required
def profile_pwd():
    if request.method == "POST":

        app.isardapi.update_user_password(current_user.id, request.form["password"])
    user = app.isardapi.get_user(current_user.id)
    return render_template("pages/user_profile.html", user=user)
