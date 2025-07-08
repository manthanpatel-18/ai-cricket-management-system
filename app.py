from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify # Added jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Initialize Flask App and MongoDB
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # CHANGE THIS IN PRODUCTION
app.config['MONGO_URI'] = 'mongodb://localhost:27017/sports_app'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads') # Use absolute path
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'jfif'}
mongo = PyMongo(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def handle_file_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}") # Add timestamp
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            return filename
        except Exception as e:
            app.logger.error(f"Error saving file {filename}: {e}") # Log errors
            flash(f"Error saving file: {e}", "danger")
            return None
    elif file and file.filename != '': # Check if file exists but is not allowed
        flash(f"File type not allowed for {file.filename}. Allowed types: {', '.join(app.config['ALLOWED_EXTENSIONS'])}", "warning")
    return None

def get_pending_match_requests(user_id):
    user_teams = list(mongo.db.teams.find({'user_id': ObjectId(user_id)}, {'_id': 1}))
    user_team_ids = [team['_id'] for team in user_teams]
    pending_requests = list(mongo.db.match_requests.find({
        'opponent_id': {'$in': user_team_ids},
        'status': 'pending'
    }).sort('created_at', -1))
    return pending_requests

def get_team_match_history(team_id):
    try:
        team_object_id = ObjectId(team_id)
    except Exception:
        return [] # Return empty list if ID is invalid

    matches = list(mongo.db.match_requests.find({
        '$or': [
            {'team_id': team_object_id},
            {'opponent_id': team_object_id}
        ],
        'status': {'$in': ['accepted', 'rejected', 'completed']}
    }).sort('created_at', -1))

    for match in matches:
        team_is_challenger = match['team_id'] == team_object_id
        match['is_challenger'] = team_is_challenger

        if team_is_challenger:
            match['opponent_name'] = match.get('opponent_name', 'Unknown Team') # Use opponent_name directly
            match['this_team_name'] = match.get('team_name', 'Unknown Team')
        else:
            # If this team was the opponent, the 'opponent' is the challenger team
            match['opponent_name'] = match.get('team_name', 'Unknown Team')
            match['this_team_name'] = match.get('opponent_name', 'Unknown Team')


        match['match_date'] = match.get('responded_at', match.get('created_at'))

        if match['status'] == 'completed':
            match['result_available'] = True
            winning_team_id = match.get('winning_team_id')
            if winning_team_id:
                 match['outcome'] = 'Win' if str(winning_team_id) == str(team_id) else 'Loss'
            elif match.get('is_draw', False):
                 match['outcome'] = 'Draw'
            else:
                 match['outcome'] = 'N/A'
            # Get scores (adjust based on role if needed, depends on how you store scores)
            match['team_score'] = match.get('team1_score' if team_is_challenger else 'team2_score', {})
            match['opponent_score'] = match.get('team2_score' if team_is_challenger else 'team1_score', {})
        else:
            match['result_available'] = False
            match['outcome'] = match['status'].capitalize()

    return matches

# --- Routes ---

@app.route('/')
def home():
    teams = list(mongo.db.teams.find().limit(6))
    upcoming_matches = list(mongo.db.match_requests.find(
        {'status': 'accepted'}
    ).sort('created_at', -1).limit(6))
    current_time = datetime.utcnow()

    # Aggregate player achievements efficiently
    pipeline = [
        {'$sort': {'runs': -1}},  # Sort by runs descending
        {'$lookup': {              # Join with teams to get team name and player profile pic
            'from': 'teams',
            'localField': 'team_id',
            'foreignField': '_id',
            'as': 'team_info'
        }},
        {'$unwind': '$team_info'}, # Deconstruct the team_info array
        {'$limit': 10},           # Get top 10 initially (more than 5 to allow for player lookup)
        {'$project': {             # Shape the output
            '_id': 0,
            'player_name': 1,
            'runs': 1,
            'wickets': {'$ifNull': ['$wickets', 0]}, # Handle missing wickets
            'team_name': '$team_info.team_name',
            # Find the specific member's profile pic within the team's members array
            'profile_pic': {
                '$let': {
                    'vars': {
                        'member': {
                            '$filter': {
                                'input': '$team_info.members',
                                'as': 'm',
                                'cond': {'$eq': ['$$m.name', '$player_name']}
                            }
                        }
                    },
                    'in': {'$arrayElemAt': ['$$member.profile_pic', 0]}
                }
            }
        }}
    ]
    mvps = list(mongo.db.player_achievements.aggregate(pipeline))[:5] # Limit to final 5

    return render_template('home.html', teams=teams, matches=upcoming_matches, now=current_time, mvps=mvps)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        existing_user = mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]})
        if existing_user:
            flash('Username or Email already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user_id = mongo.db.users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at':datetime.utcnow()
        }).inserted_id

        session['user_id'] = str(user_id)
        flash('Registration successful! Welcome.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = mongo.db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user_id_obj = ObjectId(session['user_id'])
        user = mongo.db.users.find_one({'_id': user_id_obj})
        if not user:
             # Handle case where user ID in session is invalid
             session.pop('user_id', None)
             flash('Session expired or invalid. Please log in again.', 'warning')
             return redirect(url_for('login'))

        user_data = {'username': user['username'], '_id': str(user['_id'])}
        teams = list(mongo.db.teams.find({'user_id': user_id_obj}))
        # Fetch requests initiated by the user
        sent_match_requests = list(mongo.db.match_requests.find({'user_id': user_id_obj}).sort('created_at', -1))
        # Fetch pending requests where the user is the opponent
        pending_match_requests = get_pending_match_requests(session['user_id'])
        is_new_user = len(teams) == 0
        current_year = datetime.now().year

        return render_template(
            'dashboard.html',
            user=user_data,
            teams=teams,
            sent_requests=sent_match_requests, # Renamed for clarity
            pending_requests=pending_match_requests,
            is_new_user=is_new_user,
            current_year=current_year
        )
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {e}")
        flash("An error occurred while loading the dashboard. Please try again.", "danger")
        # Log out user if ObjectId is invalid
        if "is not a valid ObjectId" in str(e):
            session.pop('user_id', None)
            return redirect(url_for('login'))
        return redirect(url_for('home')) # Or some other error page

# Add Team Members Route
@app.route('/add_team_members', methods=['GET', 'POST'])
def add_team_members():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        team_name = request.form['team_name']
        captain_name = request.form['captain_name']
        team_logo_file = request.files.get('team_logo')
        team_logo = handle_file_upload(team_logo_file) if team_logo_file else None

        members = []
        member_names = request.form.getlist('member_names[]') # Use getlist

        for i, name in enumerate(member_names):
            if not name.strip(): continue # Skip empty names
            profile_pic_file = request.files.get(f'member_profile_pic_{i}')
            profile_pic = handle_file_upload(profile_pic_file) if profile_pic_file else None
            members.append({'name': name.strip(), 'profile_pic': profile_pic})

        if not team_name.strip() or not captain_name.strip():
             flash("Team Name and Captain Name are required.", "warning")
             return render_template('add_team_members.html') # Re-render form
        if not members:
             flash("Please add at least one team member.", "warning")
             return render_template('add_team_members.html') # Re-render form


        team_data = {
            'team_name': team_name.strip(),
            'captain_name': captain_name.strip(),
            'team_logo': team_logo,
            'members': members,
            'user_id': ObjectId(session['user_id']),
            'created_at': datetime.utcnow()
        }
        mongo.db.teams.insert_one(team_data)

        flash('Team added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_team_members.html')

# Edit Team Route
@app.route('/edit_team/<team_id>', methods=['GET', 'POST'])
def edit_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        team_id_obj = ObjectId(team_id)
        user_id_obj = ObjectId(session['user_id'])
    except Exception:
        flash('Invalid Team ID.', 'danger')
        return redirect(url_for('dashboard'))

    team = mongo.db.teams.find_one({'_id': team_id_obj, 'user_id': user_id_obj})
    if not team:
        flash('Team not found or you do not have permission to edit.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        team_name = request.form['team_name']
        captain_name = request.form['captain_name']
        team_logo = team.get('team_logo') # Keep existing logo by default

        if 'team_logo' in request.files and request.files['team_logo'].filename:
            new_logo = handle_file_upload(request.files['team_logo'])
            if new_logo: team_logo = new_logo # Update only if upload successful

        members = []
        member_names = request.form.getlist('member_names[]')
        existing_members_dict = {m['name']: m.get('profile_pic') for m in team.get('members', [])}

        for i, name in enumerate(member_names):
             if not name.strip(): continue
             profile_pic = existing_members_dict.get(name.strip()) # Default to existing pic
             if f'member_profile_pic_{i}' in request.files and request.files[f'member_profile_pic_{i}'].filename:
                 new_pic = handle_file_upload(request.files[f'member_profile_pic_{i}'])
                 if new_pic: profile_pic = new_pic # Update only if upload successful
             members.append({'name': name.strip(), 'profile_pic': profile_pic})

        if not team_name.strip() or not captain_name.strip():
             flash("Team Name and Captain Name are required.", "warning")
             return render_template('edit_team.html', team=team) # Re-render form with current data
        if not members:
             flash("Please add at least one team member.", "warning")
             return render_template('edit_team.html', team=team) # Re-render form with current data


        mongo.db.teams.update_one(
            {'_id': team_id_obj},
            {'$set': {
                'team_name': team_name.strip(),
                'captain_name': captain_name.strip(),
                'team_logo': team_logo,
                'members': members,
                'updated_at': datetime.utcnow()
            }}
        )
        flash('Team updated successfully!', 'success')
        # Redirect to team details page after editing
        return redirect(url_for('view_team', team_id=team_id))

    return render_template('edit_team.html', team=team)

# View Team Details Route
@app.route('/team/<team_id>')
def view_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        team_id_obj = ObjectId(team_id)
        team = mongo.db.teams.find_one({'_id': team_id_obj})
    except Exception:
        flash('Invalid Team ID.', 'danger')
        return redirect(url_for('dashboard'))

    if not team:
        flash('Team not found.', 'danger')
        return redirect(url_for('dashboard'))

    is_owner = str(team.get('user_id', '')) == session['user_id']
    match_history = get_team_match_history(team_id)

    # Get player achievements and merge with member list
    player_achievements = list(mongo.db.player_achievements.find({'team_id': team_id_obj}))
    achievements_by_player = {ach['player_name']: ach for ach in player_achievements}
    players_with_stats = []
    for player in team.get('members', []):
        ach = achievements_by_player.get(player['name'], {})
        players_with_stats.append({
            'name': player['name'],
            'profile_pic': player.get('profile_pic'),
            'runs': ach.get('runs', 0),
            'wickets': ach.get('wickets', 0),
            'matches_played': ach.get('matches_played', 0)
        })

    return render_template(
        'team_details.html',
        team=team,
        is_owner=is_owner,
        match_history=match_history,
        players=players_with_stats # Pass combined list
    )

# Delete Team Route
@app.route('/delete_team/<team_id>')
def delete_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        team_id_obj = ObjectId(team_id)
        user_id_obj = ObjectId(session['user_id'])
    except Exception:
        flash('Invalid Team ID.', 'danger')
        return redirect(url_for('dashboard'))

    # Add deletion logic for associated data (optional but recommended)
    # e.g., delete player achievements, potentially update match requests involving this team

    result = mongo.db.teams.delete_one({'_id': team_id_obj, 'user_id': user_id_obj})

    if result.deleted_count > 0:
         # Also delete associated player achievements
        mongo.db.player_achievements.delete_many({'team_id': team_id_obj})
        flash('Team and associated achievements deleted successfully!', 'success')
    else:
        flash('Team not found or you do not have permission to delete.', 'danger')

    return redirect(url_for('dashboard'))

# Team Achievements Route
@app.route('/team/<team_id>/achievements', methods=['GET', 'POST'])
def team_achievements(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        team_id_obj = ObjectId(team_id)
        user_id_obj = ObjectId(session['user_id'])
    except Exception:
        flash('Invalid Team ID.', 'danger')
        return redirect(url_for('dashboard'))

    team = mongo.db.teams.find_one({'_id': team_id_obj})
    if not team:
        flash('Team not found.', 'danger')
        return redirect(url_for('dashboard'))

    is_owner = str(team.get('user_id', '')) == session['user_id']
    if not is_owner:
        flash('You do not have permission to edit achievements for this team.', 'warning')
        return redirect(url_for('view_team', team_id=team_id))

    achievements_by_player = {
        ach['player_name']: ach for ach in mongo.db.player_achievements.find({'team_id': team_id_obj})
    }

    if request.method == 'POST':
        for player in team.get('members', []):
            player_name = player['name']
            # Use .get with default '0', then handle potential empty string before int conversion
            runs_str = request.form.get(f'runs_{player_name}', '0').strip()
            wickets_str = request.form.get(f'wickets_{player_name}', '0').strip()
            matches_str = request.form.get(f'matches_{player_name}', '0').strip()

            try:
                runs = int(runs_str) if runs_str else 0
                wickets = int(wickets_str) if wickets_str else 0
                matches_played = int(matches_str) if matches_str else 0
            except ValueError:
                flash(f"Invalid input for player {player_name}. Please enter numbers.", "warning")
                # Continue to process others, but don't redirect yet if error
                # Or you could choose to return here
                continue # Skip this player on error


            update_data = {
                'runs': runs,
                'wickets': wickets,
                'matches_played': matches_played,
                'updated_at': datetime.utcnow()
            }

            # Use update_one with upsert=True to handle both insert and update
            mongo.db.player_achievements.update_one(
                {'team_id': team_id_obj, 'player_name': player_name},
                {'$set': update_data,
                 '$setOnInsert': { # Fields to set only on insert
                     'profile_pic': player.get('profile_pic'),
                     'created_at': datetime.utcnow()
                 }},
                upsert=True
            )

        flash('Player achievements updated successfully!', 'success')
        return redirect(url_for('view_team', team_id=team_id))

    # Prepare data for GET request rendering
    players_with_achievements = []
    for player in team.get('members', []):
        ach = achievements_by_player.get(player['name'], {})
        players_with_achievements.append({
            'name': player['name'],
            'profile_pic': player.get('profile_pic'),
            'runs': ach.get('runs', 0),
            'wickets': ach.get('wickets', 0),
            'matches_played': ach.get('matches_played', 0)
        })

    return render_template(
        'team_achievements.html',
        team=team,
        players=players_with_achievements,
        is_owner=is_owner # Pass is_owner to template
    )

# Match Request Routes
@app.route('/match_request', methods=['GET', 'POST'])
def match_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id_obj = ObjectId(session['user_id'])
    user_teams = list(mongo.db.teams.find({'user_id': user_id_obj}))
    # Exclude user's own teams from opponent list
    other_teams = list(mongo.db.teams.find({'user_id': {'$ne': user_id_obj}}))

    if not user_teams:
        flash("You need to create a team before you can request a match.", "warning")
        return redirect(url_for('add_team_members'))

    if request.method == 'POST':
        team_id = request.form.get('team_id')
        opponent_id = request.form.get('opponent_id')

        if not team_id or not opponent_id:
            flash("Please select both your team and an opponent team.", "warning")
            return render_template('match_request.html', user_teams=user_teams, other_teams=other_teams)

        try:
            team = mongo.db.teams.find_one({'_id': ObjectId(team_id), 'user_id': user_id_obj})
            opponent = mongo.db.teams.find_one({'_id': ObjectId(opponent_id)})
        except Exception:
             flash("Invalid team selection.", "danger")
             return render_template('match_request.html', user_teams=user_teams, other_teams=other_teams)


        if not team or not opponent:
            flash('Selected team(s) not found or invalid selection.', 'danger')
            return render_template('match_request.html', user_teams=user_teams, other_teams=other_teams)

        # Check for existing pending request between these two teams
        existing_request = mongo.db.match_requests.find_one({
             '$or': [
                 {'team_id': team['_id'], 'opponent_id': opponent['_id']},
                 {'team_id': opponent['_id'], 'opponent_id': team['_id']}
             ],
             'status': 'pending'
        })
        if existing_request:
            flash(f"There is already a pending match request between {team['team_name']} and {opponent['team_name']}.", 'warning')
            return redirect(url_for('dashboard'))


        match_request_data = {
            'user_id': user_id_obj, # User who initiated
            'team_id': team['_id'], # User's team (challenger)
            'team_name': team['team_name'],
            'opponent_id': opponent['_id'],
            'opponent_name': opponent['team_name'],
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        mongo.db.match_requests.insert_one(match_request_data)
        flash('Match request sent successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('match_request.html', user_teams=user_teams, other_teams=other_teams)

@app.route('/match_request/respond/<request_id>/<action>')
def respond_to_match_request(request_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        request_id_obj = ObjectId(request_id)
        user_id_obj = ObjectId(session['user_id'])
    except Exception:
        flash('Invalid Request ID.', 'danger')
        return redirect(url_for('dashboard'))

    match_request = mongo.db.match_requests.find_one({'_id': request_id_obj, 'status':'pending'})
    if not match_request:
        flash('Match request not found or already responded to.', 'warning')
        return redirect(url_for('dashboard'))

    # Verify the current user owns the opponent team of this request
    if match_request['opponent_id'] not in [t['_id'] for t in mongo.db.teams.find({'user_id': user_id_obj}, {'_id': 1})]:
        flash('You do not have permission to respond to this request.', 'danger')
        return redirect(url_for('dashboard'))

    valid_actions = ['accept', 'reject']
    if action not in valid_actions:
        flash('Invalid action.', 'danger')
        return redirect(url_for('dashboard'))

    new_status = 'accepted' if action == 'accept' else 'rejected'
    mongo.db.match_requests.update_one(
        {'_id': request_id_obj},
        {'$set': {'status': new_status, 'responded_at': datetime.utcnow()}}
    )

    flash(f'Match request {action}ed.', 'success' if action == 'accept' else 'info')
    return redirect(url_for('dashboard'))

@app.route('/match_request/cancel/<request_id>')
def cancel_match_request(request_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        request_id_obj = ObjectId(request_id)
        user_id_obj = ObjectId(session['user_id'])
    except Exception:
        flash('Invalid Request ID.', 'danger')
        return redirect(url_for('dashboard'))

    # Only the user who created the request can cancel it, and only if pending
    result = mongo.db.match_requests.delete_one({
        '_id': request_id_obj,
        'user_id': user_id_obj,
        'status': 'pending'
    })

    if result.deleted_count > 0:
        flash('Match request canceled.', 'success')
    else:
        flash('Could not cancel request. It might not exist, not be pending, or you didn\'t create it.', 'warning')

    return redirect(url_for('dashboard'))


# *** NEW SCOUTING ENDPOINT ***
# *** MODIFIED SCOUTING ENDPOINT ***
@app.route('/scout_players/<team_id>')
def scout_players(team_id):
    # No need for session check here if anyone can view the stats of a team they are looking at
    # However, you might want to add it back if scouting is restricted

    try:
        viewed_team_id = ObjectId(team_id)
        # You might fetch the team name here if needed for the modal title later, though the JS already has it
        # team = mongo.db.teams.find_one({'_id': viewed_team_id}, {'team_name': 1})
        # if not team:
        #     return jsonify({'error': 'Team not found'}), 404

    except Exception:
        return jsonify({'error': 'Invalid Team ID'}), 400

    # Fetch player achievements specifically for THIS team
    pipeline = [
         # Match players belonging ONLY to the current team
        {'$match': {'team_id': viewed_team_id}},
        {'$sort': {'runs': -1}},  # Sort by runs descending
        # Optional: Lookup team info if needed, but less critical now
        # {$lookup: ...}
        # {$unwind: ...}
        {'$limit': 3},           # Get top 3 players from this team
        {'$project': {            # Shape the output
            '_id': 0,
            'name': '$player_name',
            'runs': {'$ifNull': ['$runs', 0]},
            'wickets': {'$ifNull': ['$wickets', 0]},
            'matches_played': {'$ifNull': ['$matches_played', 0]},
            'scoutScore': {'$ifNull': ['$runs', 0]}, # Use runs as scout score
            'profile_pic': '$profile_pic', # Directly use the stored pic if available
            # 'role': 'Unknown', # Placeholder if needed
            # 'region': 'Unknown', # Placeholder if needed
        }}
    ]

    # Execute the aggregation pipeline
    top_players_in_team = list(mongo.db.player_achievements.aggregate(pipeline))

    # Since profile_pic might not be stored in achievements consistently,
    # let's fetch the team members once and merge the profile pics
    team_members = mongo.db.teams.find_one({'_id': viewed_team_id}, {'members.name': 1, 'members.profile_pic': 1})
    member_pics = {m['name']: m.get('profile_pic') for m in team_members.get('members', [])} if team_members else {}

    # Add profile pics to the results if missing from achievements collection
    for player in top_players_in_team:
        if not player.get('profile_pic') and player['name'] in member_pics:
            player['profile_pic'] = member_pics[player['name']]

    return jsonify(top_players_in_team)

# --- Keep the rest of your app.py code as it was ---
# (home, register, login, dashboard, add_team_members, edit_team, view_team,
# delete_team, team_achievements, match request routes, logout, etc.)

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)