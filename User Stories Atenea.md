# User Stories

## Integrative Project: [Atenea.io](http://atenea.io/)

## User Stories - MPA with Vertical Scalability and Gamification

## Project Context

An educational institution needs to modernize its academic management with a Multiple Page Application (MPA) built in pure JavaScript (Vanilla JS / Vite). The platform, called [Atenea.io](http://Atenea.io), integrates role-based authentication, CRUD operations for grades, course and schedule management, institutional announcements, and a multi-type gamification system. The technical design incorporates vertical scalability: the architecture must be able to scale in capacity (more users, more data, more modules) without redesigning its foundation.

System roles: Chancellor (admin) • Professor (teacher) • Student (end user).

## Applied Principles for Vertical Scalability

- Server-side pagination on all listings (?_page=&_limit=) to avoid overloading the client.
- Perform aggregate calculations (averages, leaderboards) on the server—never on the client.
- Extensible data schema: new data types, roles, or modules can be added without changing existing structures.
- Decoupled router and modules: each feature is a plugin that registers itself, rather than modifying the core.
- Strict separation of layers (UI / Services / Store / Router) to make each layer easy to scale independently.

## Authentication and Session

## US-01

**Priority: High**

As a registered user, I want to log in to the [Atenea.io](http://atenea.io/) platform using my email address and password to access only the features and data corresponding to my role.

### Acceptance Criteria

- The form validates that the email address is in a valid format and that the password is not empty.
- Credentials are verified against the json-server endpoint/users (or external API).
- After a successful login, the user is automatically redirected to the dashboard for the corresponding role (university president / professor / student).
- If the credentials are incorrect, a descriptive error message is displayed without revealing which field failed.
- The session is stored in localStorage (the “remember me” option) or sessionStorage (tab session).

### Restrictions

- A user cannot access modules intended for another role.
- After 3 consecutive failed attempts, the login button is disabled for 30 seconds.

Vertical scalability: The authentication module must be stateless to allow horizontal replication of the frontend without losing sessions.

Technical note: Implement as a standalone page (MPA): /login.html. The router redirects here when there is no active session.

## US-02

**Priority: High**

As an authenticated user, I want to keep my session active when refreshing or navigating between pages in the MPA, so that my workflow isn’t interrupted by accidental page reloads.

### Acceptance Criteria

- When refreshing any page, the session is automatically retrieved from localStorage/sessionStorage.
- The router verifies the token/session before rendering any protected modules.
- If the session has expired, the user is redirected to /login.html with an informational message.
- Logging out completely clears localStorage and sessionStorage and redirects to /login.html.

Vertical Scalability: Design the guard as a pure, reusable function to facilitate the addition of new roles without modifying the core logic.

Technical note: Use a route guard/middleware in the MPA router that runs before every page change.

## Rector (Admin)

## US-03

**Priority: High**

As rector, I want to manage institutional announcements and notices (create, edit, delete) to keep the entire educational community informed in a centralized and timely manner.

### Acceptance Criteria

- The rector can create a communication with a title, body, publication date, and recipient (everyone / faculty / students).
- Communications appear on the recipient’s dashboard in reverse chronological order.
- The rector can edit or delete an existing communication; changes are reflected in real time for recipients.
- Each communication is logged with a date, author and status (Published/Draft).

Vertical scalability: The announcements table must support server-side pagination to maintain
performance with thousands of records.

Technical note: CRUD operations on /comunicados in json-server. Filter by target role in the dashboard GET request.

## US-04

**Priority: High**

As the university president, I want to create, edit, deactivate, and view courses along with their schedules and enrollment capacities, in order to
organize and update the academic offerings without relying on manual paper records

### Acceptance Criteria

- Each course contains: ID, name/grade level, subject, assigned instructor, schedule (day and time), maximum capacity, and
status (Active/Inactive).
• The principal can assign or reassign an instructor to a course from a user selector with the “teacher” role.
• When a course is deactivated, enrolled students receive a notification on their dashboard.
• The dean can change a course’s schedule; the change is reflected in the instructor’s calendar and that of the
enrolled students.
• Two courses with the same instructor cannot be created for the same time slot.

## Restrictions

- You cannot delete a course with recorded grades; you can only deactivate it.

Vertical scalability: The course model must support multiple locations without changes to the data structure
(add “locationId” field).

Technical note: CRUD /courses. Validate schedule conflicts before POST/PATCH.

## US-05

**Priority: High**

As the rector, I want to manage the entire student registration process (enrollment, editing, course assignment,
and withdrawal) to keep the academic roster up to date and ensure that every student is
properly enrolled.

### Acceptance Criteria

- The dean can enroll a new student by entering their name, email address, temporary password, and
initial course assignment.
• The president can edit personal information and reassign courses for any student.
• When a student is withdrawn, their status changes to “Inactive”; their grades and academic history are retained.
• The student list supports searching by name, course, and status.

Vertical scalability:  Implement server-side pagination (?_page=&_limit=) to scale to thousands of
students without degrading initial load performance.

Technical note: CRUD /users filtering by role:“student”. The search uses json-server query parameters
(?name_like=).

## US-06

Prioridad: Alta

As the university president, I want to manage the registration of faculty members and their course assignments to ensure full faculty coverage and avoid scheduling conflicts.

### Acceptance Criteria

- The university president can create, edit, and deactivate faculty accounts.
- All assigned courses are displayed in the faculty member’s profile.
- A faculty member with active courses cannot be deactivated without first reassigning those courses.

Technical Note: CRUD /users filtering by role: “teacher”. Validate dependencies in DELETE/PATCH.

## US-07

Priority: Medium

As the university president, I want to view a dashboard with overall academic statistics and metrics so I can make informed decisions about institutional performance without needing manual reports.

### Acceptance Criteria

- The dashboard displays: overall grade average by course and term, number of active/inactive students, and the top 5 students by gamification points.
- The metrics are recalculated upon entering the module (fresh GET request to the API).
- It allows filtering by academic term.

Vertical scalability: Statistical calculations must be performed on the server (json-server + middleware or external API) to avoid overloading the client as data volume grows.

## US-08

Priority: Medium

As the university president, I want to configure and expand the point types in the gamification system to tailor academic motivation to different pedagogical goals without disrupting the existing system.

### Acceptance Criteria

- The university president can create a new point type with a name, icon/color, and description.
- When a new type is added, the global leaderboard is automatically updated to include it.
- A point type can be deactivated; points already awarded of that type are retained.
- The system is never limited to a single “currency”: Excellence Points, Attitude Points, Participation Tokens, etc., can coexist.

## Restrictions

- Only the principal can create or deactivate point types.

Vertical scalability: The point type schema must be extensible without destructive migrations: adding a new type is a simple POST, not an ALTER TABLE.

Technical note: CRUD /pointTypes. The /studentPoints table references pointType id, never a hardcoded field.

## Profesor (Teacher)

## US-09

Priority: High

As a teacher, I want to view the list of courses I’m assigned to and access the details for each one, so I can plan my teaching and quickly access my students and subjects.

### Acceptance Criteria

- The teacher dashboard displays only the courses for which the teacher is listed as the assigned instructor.
- Each course card displays: subject, grade level, schedule, and number of enrolled students.
- Clicking on a course opens its details page with a list of students and access to grade management.

Technical note: GET/courses?teacherld={userld}. Standalone page/courses-teacher.html in the MPA.

## US-10

Priority: High

As a professor, I want to record, edit, publish, and delete student grades for my courses in order to keep the academic transcript up to date and control when students can view their grades.

### Acceptance Criteria

- The instructor can create a grade with: student, course, period, numerical value, and automatically calculated performance (Failing <3.0 / Minimum 3.0–3.9 / Satisfactory 4.0–4.4 / Advanced 4.5–5.0).
- A grade with the “Draft” status is not visible to the student.
- When a grade is published (status changed to “Published”), the student’s transcript is automatically updated.
- The instructor can only view and manage grades for the courses assigned to them.
- A grade can only be deleted if it is in “Draft” status.

## Restrictions

- The dean can view any grade but cannot create or edit them.
- Students cannot view grades in Draft status.

Vertical scalability: The grades endpoint must support combined filters
(?studentID=&courseID=&period=) to scale without loading the full dataset on the client side.

Technical note: CRUD /grades. Always filter by courseID belonging to the authenticated instructor (client-side validation + API).

## US-11

Priority: High

As a teacher, I want to award gamification points to my students by subject, specifying the reason and type of point, in order to systematically recognize their effort and academic achievements and encourage student engagement.

### Acceptance Criteria

- The teacher selects a student from their class, the type of point (based on the dean’s settings), and a quantity.
- The teacher must enter a descriptive reason (e.g., “Excellent oral presentation”).
- Each assignment is recorded with the date, reason, point type, amount, and the teacher who awarded it.
- The student’s point balance is immediately updated on the leaderboard.
- Only the teacher can award points; the dean can audit the history.

## Restrictions

- Students cannot award points to themselves.
- Professors can only award points in the courses they teach.

Vertical scalability: Storing points as individual transactions (lightweight event sourcing) allows for full auditing and makes it easy to add new point types without rewriting the history.

Technical note: POST /studentPoints {studentId, courseId, pointTypeId, amount, reason, teacherId, date}. The total points are recalculated with every query of the leaderboard.

## US-12

Priority: Medium

As a professor, I want to view my class schedule and receive institutional announcements from the president so I can organize my day and stay informed about the latest news without relying on external channels.

### Acceptance Criteria

- The “My Schedule” section displays a weekly view of assigned courses, including the day and time.
- Announcements from the president appear on the dashboard sorted in descending order by date.
- Unread announcements are visually highlighted.

## Student (User)

## US-13

Priority: High

As a student, I want to view my transcript by course and academic term so I can continuously track my performance without needing intermediaries.

### Acceptance Criteria

- The transcript displays only grades with the “Published” status that correspond to the authenticated student.
- Each row displays: course, term, numerical grade, performance, and instructor’s name.
- The student can filter by academic term.
- The overall GPA for the term is calculated and displayed at the top of the transcript.

## Restrictions

- Students cannot view other students’ grades.
- They cannot modify any grades.

Technical note: GET/notas?estudianteld={userld}&estado=Publicada. Render on the dedicated /boletin.html page of the MPA.

## US-14

Priority: High

As a student, I want to see the courses I’m enrolled in, their announcements, and the academic calendar, so I can have all the relevant information about my academic activities in one place.

### Acceptance Criteria

- The dashboard displays cards for each course I’m enrolled in, showing the subject, grade level, and schedule.
- Course announcements and institutional notices are displayed in a separate section, sorted by date.
- The calendar displays important dates for the academic year.

## US-15

Priority: High

As a student, I want to see my total score, broken down by point type and subject, and view the leaderboard to see my position in the gamification system and motivate myself to improve my performance.

## Acceptance Criteria

- The “My Points” section displays the current balance for each active point type.
- There is a breakdown by course: how many points were earned in each course and of what type.
- The leaderboard shows the rankings of all students in the same course/grade.
- The leaderboard can be filtered by point type or viewed as an overall ranking (total of all types).
- Students cannot see the exact point balances of others (only the ranking).

Vertical scalability: The leaderboard is always generated on the server using an aggregate query, rather than loading all records on the client side, to scale to thousands of students.

## US-16

Priority: Medium

As a student, I want to redeem my points in the rewards store for academic or institutional benefits, to receive tangible recognition for my efforts and maintain long-term motivation.

## Acceptance Criteria

- The store displays available rewards along with their point cost (by type).
- Students can only redeem rewards if they have a sufficient balance of the required point type.
- Upon redemption, the balance is deducted, and a record of the transaction is kept.
- The redemption history is visible to both the student and the dean.

## Restrictions

- Redeemed points cannot be automatically reversed; they require the dean’s approval.

Vertical scalability: The rewards catalog must be configurable by the dean without code changes, to add or remove rewards based on the academic year.

Technical note: POST /redemptions {studentId, rewardId, pointsUsed, pointTypeId}. Verify sufficient balance before committing.

## US-17

Priority: Low

As a student, I want to view and edit my personal profile (name, photo, password) to keep my information up to date and customize my experience on the platform.

## Acceptance Criteria

- The student can change their name, profile photo, and password.
- Changing the password requires confirming the current password.
- Changes are persisted in /users via PATCH.

## MPA - Architecture and Navigation

## US-18

Priority: High

As a user, I want to navigate between the platform’s modules without full page reloads, to have a smooth experience similar to a native app, reducing wait times.

## Acceptance Criteria

- The application implements a client-side router based on the History API or hash (#).
- Each route change dynamically renders the corresponding module in the main container without reloading the base HTML.
- The browser’s Back/Forward buttons work correctly.
- Protected routes (any module other than login) redirect to /login.html if there is no active session.
- When copying and pasting a direct URL, the application loads the correct page or redirects to the login page.

Vertical scalability: The router must allow new routes to be added via a simple registration (router.register(“/new-route”, handler)) without modifying the router’s core.

Technical note: Implement a Router class with methods navigate(route), register(route, handler), and guardsMiddleware[]. Each module exports its own rendering function.

## US-19

Priority: High

As a developer, I want to structure the application into independent modules with a clear separation of responsibilities to facilitate maintenance, testing, and vertical scalability of the project.

## Acceptance Criteria

- Each module (auth, courses, grades, gamification, announcements) resides in its own folder with its partial HTML, JS, and CSS.
- API services (fetch) are centralized in a /services layer separate from the UI.
- Session state is managed in a centralized /store module.
- There is no business logic in the view files (partial HTML).

Vertical Scalability: The modular architecture allows for vertical scaling by adding new modules (e.g., messaging, attendance) without refactoring existing ones.

Technical note: Suggested architecture: /pages (HTML partials), /services (fetch API), /store (session), /router (router), /components (reusable UI elements).

|   **——————** | ——————— |      **User Story          Summary** | ——————— | ——————— |
| --- | --- | --- | --- | --- |
| ID | Rol | Story | Priority | Module |
| US-01  | Student/Rector/Teacher | Log in with credentials | High | Auth |
| US-02 | Authenticated User | Maintain session on refresh | High | Auth |
| US-03 | Rector | Manage institutional communications | High | Communications |
| US-04 | Rector | Create and manage courses with schedules | High | Courses |
| US-05 | Rector | Manage student registration | High | Users |
| US-06 | Rector | Manage faculty registration | High | Users |
| US-07 | Rector | View dashboard with indicators | Medium | Dashboard |
| US-08 | Rector | Configure point types (gamification) | Medium | Gamification |
| US-09 | Teacher | View assigned courses |  | Courses |
| US-10 | Teacher | Register and publish grades | High | Grades |
| US-11 | Teacher | Assign gamification points | High | Gamification |
| US-12 | Teacher | View schedule and announcements | Medium | Announcements |
| US-13 | Student | Check report card | High | Grades |
| US-14 | Student | Check report card | High | Courses |
| US-15 | Student | View points and leaderboard | High | Gamification |
| US-16 | Student | Redeem points in store | Medium | Gamification |
| US-17 | Student | Edit personal profile | Low | Profile |
| US-18 | User | Browse without recharging (MPA router) | High | MPA |
| US-19 | Developer | Scalable modular architecture | High | MPA |