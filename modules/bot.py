<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AutoTyper-Z Home</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav>
        <a href="{{ url_for('home') }}">Home</a> |
        <a href="{{ url_for('start_bot') }}">Start Bot</a> |
        <a href="{{ url_for('dashboard') }}">Dashboard</a>
    </nav>
    <h1>Welcome to AutoTyper-Z Bot Command Center</h1>
    <p>Your NitroType bot manager web interface.</p>
</body>
</html>
