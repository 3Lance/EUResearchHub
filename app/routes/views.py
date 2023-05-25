
import time

from flask import Blueprint, render_template, request, redirect, url_for, flash, get_flashed_messages, session, abort
from flask_login import login_required, current_user


from app.models.database import db, Evaluation_Windows, Projects,ProjectsStatusCount, Researchers, Researchers_Projects, Documents, Evaluation_Reports, Researchers_Projects

views = Blueprint('views', __name__)


@views.route('/')
@login_required
def home():
    return render_template('index.html')


from sqlalchemy import func


@views.route('/projects')
@login_required
def projects():
    projects2show = Projects.query.all()
    user_type = session['user_type']
    # delete the get params

    user = current_user

    counts_by_status = {
        'approved': 0,
        'require changes': 0,
        'submitted for evaluation': 0,
        'not approved': 0
    }

    if user_type == 'evaluator':
        print('evaluator')
        projects2show = Projects.query.all()
        project_counts = ProjectsStatusCount.query.all()
        for row in project_counts:
            counts_by_status[row.status.value] = row.count

    elif user_type == 'researcher':
        print('researcher')
        projects2show = db.session.query(Projects).join(Researchers_Projects).filter(Researchers_Projects.fk_researchers == user.id).all()
        project_counts = db.session.query(Projects.status, func.count()).join(Researchers_Projects).filter(Researchers_Projects.fk_researchers == user.id).group_by(Projects.status).all()
        aux = {status.value: count for status, count in project_counts}
        counts_by_status = {**counts_by_status, **aux}

        print (counts_by_status)



    researcher_profile_pictures = []
    for project in projects2show:
        project_id = project.id
        profile_pictures = db.session.query(Researchers.profile_picture) \
            .join(Researchers_Projects) \
            .filter(Researchers_Projects.fk_projects == project_id) \
            .all()
        researcher_profile_pictures.append(profile_pictures)

    # Aggiungi la query per ottenere la percentuale di documenti valutati per ogni progetto
    evaluation_percentages = {}
    for project in projects2show:
        project_id = project.id
        total_documents = Documents.query.filter_by(fk_project=project_id).count()
        evaluated_documents = Evaluation_Reports.query.join(Documents).filter(
            Documents.fk_project == project_id).count()

        if total_documents > 0:
            evaluation_percentage = (evaluated_documents / total_documents) * 100
        else:
            evaluation_percentage = 0.0

        evaluation_percentages[project_id] = evaluation_percentage

    from sqlalchemy import desc

    evaluation_window = db.session.query(Evaluation_Windows).order_by(desc(Evaluation_Windows.evaluation_windows_to)).first()
    evaluation_window_from = evaluation_window.evaluation_windows_from.strftime("%Y/%m")
    evaluation_window_to = evaluation_window.evaluation_windows_to.strftime("%Y/%m")

    flashed_messages = get_flashed_messages()
    print(flashed_messages)

    return render_template('projects.html',
                           name=user.name,
                           surname=user.surname,
                           from_date=evaluation_window_from,
                           to_date=evaluation_window_to,
                           counts_by_status=counts_by_status,
                           projects=projects2show,
                           researcher_profile_pictures=researcher_profile_pictures,
                           user_type=user_type,
                           profile_picture=user.profile_picture,
                           messages=flashed_messages,
                           evaluation_percentages=evaluation_percentages)


@views.route('/update_project_status', methods=['POST'])
@login_required
def update_project_status():

    project_id = request.form.get('project_id')
    new_status = request.form.get('new_status')
    print("adsfsajdfgaksdf")
    project = Projects.query.get(project_id)
    if project:
        project.status = new_status
        db.session.commit()
        flash('Project status updated successfully.', 'success')
    else:
        flash('Project not found.', 'error')

    return redirect(url_for('views.projects'))



@views.route('/add_participant', methods=['POST'])
@login_required
def add_participant():
    # Get data from the post request
    data = request.get_json()

    # Get project_id and email from the posted data
    project_id = data.get('projectId')
    email = data.get('email')
    print(project_id)
    print(email)
    # Check if the project and the researcher with the provided email exist
    project = Projects.query.get(project_id)
    researcher = Researchers.query.filter_by(email=email).first()

    if not project or not researcher:
        flash('Project or researcher does not exist.', 'error')
        # If either the project or researcher does not exist, return an error


    # Check if the researcher is already added to the project
    researcher_project = Researchers_Projects.query.filter_by(fk_projects=project_id,
                                                              fk_researchers=researcher.id).first()
    if researcher_project:
        # If the researcher is already added, return an error
        flash('Researcher is already added to this project.', 'error')

    # Create a new record
    new_researcher = Researchers_Projects(fk_researchers=researcher.id, fk_projects=project_id)

    # Add the new record to the session and commit it to the database
    db.session.add(new_researcher)

    db.session.commit()

    # Return a success response
    return redirect(url_for('views.projects'))


@views.route('/project/<int:project_id>')
@login_required
def project(project_id):
    # controllo se l'utente è un ricercatore
    if session['user_type'] == 'researcher':
        # se l'utente è ricercatore deve avere accesso al progetto
        has_access = Researchers_Projects.query.filter_by(fk_projects=project_id, fk_researchers=current_user.id).first()
        if not has_access:
            abort(403)
    return render_template('project.html', name=current_user.name, surname=current_user.surname)
