"""A larger, realistic vacancy set (Chapter 4 dataset) plus the extra skills it needs.
Replaces the 8-job placeholder list in db.py. Run `python db.py` after editing this file
to rebuild the database from scratch."""

EXTRA_SKILLS = [  # name, category, aliases — appended to db.SKILLS
    ("TypeScript", "Programming", "ts"), ("PHP", "Programming", ""), ("Go", "Programming", "golang"),
    ("Vue.js", "Web", "vue,vuejs"), ("Angular", "Web", "angularjs"), ("Spring Boot", "Web", "spring"),
    ("GraphQL", "Web", ""), ("PostgreSQL", "Database", "postgres"), ("MongoDB", "Database", "mongo"),
    ("Redis", "Database", ""), ("Kubernetes", "Tools", "k8s"), ("CI/CD", "Tools", "continuous integration,jenkins"),
    ("Terraform", "Cloud", ""), ("Azure", "Cloud", "microsoft azure"), ("Google Cloud", "Cloud", "gcp"),
    ("TensorFlow", "Data Science", ""), ("PyTorch", "Data Science", ""), ("NLP", "Data Science", "natural language processing"),
    ("Computer Vision", "Data Science", ""), ("R", "Data Science", ""), ("Tableau", "Data Science", ""),
    ("Agile", "Management", "scrum"), ("UI/UX Design", "Design", "ui design,ux design,user experience"),
    ("Figma", "Design", ""), ("Mobile Development", "Programming", "android development,ios development"),
    ("Swift", "Programming", ""), ("Kotlin", "Programming", ""), ("Penetration Testing", "Security", "pen testing"),
    ("QA Testing", "Testing", "quality assurance,manual testing"), ("Test Automation", "Testing", "selenium,automated testing"),
    ("Customer Service", "Soft Skill", "customer support"), ("Sales", "Soft Skill", ""),
    ("Content Writing", "Soft Skill", "copywriting,technical writing"), ("Leadership", "Soft Skill", "team leadership"),
]

# (title, company, location, description) — descriptions are written so the taxonomy
# (skills.py + EXTRA_SKILLS) extracts a realistic, varied set of required skills.
JOBS = [
("Junior Web Developer","Coderline","Lagos","Build and maintain websites using HTML, CSS and JavaScript. Work with React components and consume REST API endpoints. Use Git daily. Good communication and teamwork expected."),
("Senior Frontend Engineer","Brightside","Remote","Lead frontend architecture using React, TypeScript and Vue.js. Own component libraries, work closely with UI/UX Design, and mentor junior developers. Strong communication and leadership needed."),
("Full Stack Developer","Stackline","Lagos","Build features end-to-end: React on the frontend, Node.js and Flask on the backend, PostgreSQL for storage. Use Docker and Git. Comfortable with Agile ceremonies."),
("Backend Developer (Python)","Meridian Systems","Abuja","Develop REST API services with Python and Django, backed by SQL and PostgreSQL. Deploy with Docker to AWS. Git-based workflow, code review culture."),
("Backend Developer (Java)","IronGate","Port Harcourt","Build microservices in Java with Spring Boot, MongoDB and Redis. CI/CD pipelines, Kubernetes deployment. Problem solving and teamwork essential."),
("Mobile App Developer","Appworks","Remote","Build cross-platform apps; native Android development in Kotlin and iOS development in Swift. Consume REST API and GraphQL endpoints. Use Git and Figma handoffs."),
("DevOps Engineer","CloudNine","Lagos","Manage CI/CD pipelines, Docker and Kubernetes clusters on AWS and Azure. Write Terraform for infrastructure. Linux administration and networking knowledge required."),
("Site Reliability Engineer","Uptime Labs","Remote","Own production reliability: Kubernetes, Docker, Linux, monitoring and incident response. Scripting in Python, strong problem solving, on-call communication."),
("Database Administrator","DataVault","Port Harcourt","Manage production databases: SQL, PostgreSQL, database design and Linux servers. Git-based change control, performance tuning, backups."),
("Data Analyst","Nimbus Analytics","Lagos","Analyse business data using Python, SQL and Pandas. Build reports in Microsoft Excel and Power BI, apply statistics and data visualization. Communication skills required."),
("Business Intelligence Analyst","Insightful","Ibadan","Turn data into decisions with Power BI, SQL and Microsoft Excel. Data visualization, Tableau, statistics and strong communication with stakeholders."),
("Machine Learning Engineer","Cortex Labs","Remote","Train and deploy models in Python with TensorFlow and PyTorch. Solid machine learning and statistics background, SQL, Git and Docker. Problem solving mindset."),
("Data Scientist","Cortex Labs","Remote","Apply machine learning and statistics to business problems using Python, Pandas and R. Communicate findings with data visualization and Tableau. NLP experience a plus."),
("NLP Engineer","Lexicon AI","Remote","Build NLP pipelines in Python using PyTorch and TensorFlow. Strong statistics and machine learning fundamentals, SQL for data access, Git for collaboration."),
("Computer Vision Engineer","Lexicon AI","Remote","Develop Computer Vision models with Python, PyTorch and TensorFlow. Machine learning and statistics background, Docker for deployment, Git workflow."),
("Security Analyst","Shieldworks","Abuja","Monitor systems and respond to incidents. Knowledge of Cybersecurity, Penetration Testing, networking and Linux. Communication and problem solving."),
("Penetration Tester","RedTeam Nigeria","Remote","Conduct Penetration Testing and vulnerability assessments. Strong Cybersecurity, networking and Linux fundamentals. Clear written communication for reports."),
("QA Engineer","Pixelcraft","Abuja","Own QA Testing across web and mobile: manual and Test Automation with Selenium. SQL for data validation, Git, strong communication with developers."),
("Automation Test Engineer","Stackline","Lagos","Build Test Automation frameworks in Python and JavaScript. CI/CD integration, Git, SQL, strong problem solving and attention to detail."),
("Cloud Engineer","CloudNine","Remote","Design and operate cloud infrastructure on AWS, Azure and Google Cloud. Terraform, Kubernetes, Docker, Linux and networking. CI/CD experience required."),
("Product Manager","Insightful","Lagos","Own product roadmap using Agile practices. Work with SQL for metrics, Data Visualization for reporting, and strong Communication and Leadership skills."),
("UI/UX Designer","Brightside","Remote","Design interfaces in Figma, conduct user research and translate into UI/UX Design specs. Collaborate with React developers. Strong communication and Teamwork."),
("Technical Writer","DocuTech","Remote","Produce Content Writing and technical documentation for APIs and SDKs. Familiarity with REST API, Git and Markdown. Excellent written Communication."),
("Network Administrator","Shieldworks","Abuja","Maintain Networking infrastructure, Linux and Windows servers, and Cybersecurity basics. Troubleshooting and clear Communication with staff."),
("IT Support Specialist","Coderline","Lagos","Provide Customer Service and technical support to staff. Windows and Linux troubleshooting, Networking basics, Communication and Teamwork."),
("Sales Engineer","Insightful","Lagos","Support Sales with technical demos of the analytics platform, using SQL and Power BI. Strong Communication, Customer Service and problem solving."),
("Project Coordinator","Meridian Systems","Abuja","Coordinate delivery using Agile and Project Management practices. Track work in SQL-backed tools, report with Microsoft Excel. Strong Communication and Leadership."),
("Junior Data Engineer","Nimbus Analytics","Remote","Build data pipelines with Python, SQL and PostgreSQL. Work with Pandas, Docker and Git. Support Machine Learning teams with clean data."),
("PHP Developer","Coderline","Lagos","Maintain and extend web applications in PHP with SQL and MySQL-style PostgreSQL databases. HTML, CSS, JavaScript on the frontend. Git workflow."),
("Go Backend Engineer","IronGate","Remote","Build high-throughput services in Go with PostgreSQL and Redis. Docker, Kubernetes and CI/CD. Strong problem solving and code review discipline."),
]
