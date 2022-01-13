def request_to_json(request):
    data = {
        "headers":dict(request.headers),
        "body":request.get_json(silent=True),
        "form":request.form.to_dict(flat=False),
        "args":request.args.to_dict(),
    }
    for property in ["origin","method","mimetype","referrer","remote_addr","url"]:
        data[property] = getattr(request,property)
    return data
