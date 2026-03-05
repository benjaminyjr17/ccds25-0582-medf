#!/usr/bin/env python3
"""
Generate the EUR-tailored version of the Course Descriptions: Quantitative Methods PDF.
Only the introductory paragraph is changed; all other content remains identical.
"""

from fpdf import FPDF
import os

# ─── Constants ───────────────────────────────────────────────────────────────
MINUS = "\u2212"  # U+2212 MINUS SIGN

FONT_DIR = "/usr/share/fonts/truetype/carlito"
OUTPUT_PATH = "/home/ubuntu/Yick_Benjamin_Oliver_Course_Descriptions_Sufficient_Mathematical_Background_EUR.pdf"

# Colors
TITLE_COLOR = (68, 114, 195)  # Exact from original PDF
HEADING_COLOR = (68, 114, 195)
BLACK = (0, 0, 0)
TABLE_HEADER_BG = (242, 242, 242)
SEPARATOR_COLOR = (204, 204, 204)

# Page settings (A4)
PAGE_W = 210  # mm
PAGE_H = 297  # mm
MARGIN_L = 25
MARGIN_R = 25
MARGIN_T = 25
MARGIN_B = 25
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


class CourseDescriptionPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=MARGIN_B)
        self.set_margins(MARGIN_L, MARGIN_T, MARGIN_R)

        # Add Carlito fonts
        self.add_font("Carlito", "", os.path.join(FONT_DIR, "Carlito-Regular.ttf"), uni=True)
        self.add_font("Carlito", "B", os.path.join(FONT_DIR, "Carlito-Bold.ttf"), uni=True)
        self.add_font("Carlito", "I", os.path.join(FONT_DIR, "Carlito-Italic.ttf"), uni=True)
        self.add_font("Carlito", "BI", os.path.join(FONT_DIR, "Carlito-BoldItalic.ttf"), uni=True)

    def footer(self):
        pass  # No footer in original

    # ── Helpers ──────────────────────────────────────────────────────────────

    def section_title(self, text):
        """Blue section heading (e.g., 'Overview of quantitative courses')."""
        self.set_font("Carlito", "", 14)
        self.set_text_color(*HEADING_COLOR)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_text_color(*BLACK)

    def course_heading(self, text):
        """Bold course title (e.g., 'BU5401: Management Decision Tools')."""
        self.set_font("Carlito", "B", 11)
        self.set_text_color(*BLACK)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def course_meta(self, au_text, semester_text):
        """Academic Units and Semester line."""
        self.set_font("Carlito", "B", 10)
        self.cell(self.get_string_width("Academic Units: "), 5, "Academic Units: ")
        self.set_font("Carlito", "", 10)
        self.cell(self.get_string_width(au_text + "  "), 5, au_text + "  ")
        self.set_font("Carlito", "", 10)
        self.cell(self.get_string_width("| "), 5, "| ")
        self.set_font("Carlito", "B", 10)
        self.cell(self.get_string_width("Semester: "), 5, "Semester: ")
        self.set_font("Carlito", "", 10)
        self.cell(0, 5, semester_text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_heading(self, text):
        """Bold sub-heading (e.g., 'Course Objectives')."""
        self.set_font("Carlito", "B", 10)
        self.cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        """Justified body text."""
        self.set_font("Carlito", "", 10)
        self.multi_cell(CONTENT_W, 5, text, align="J")
        self.ln(2)

    def source_line(self, text):
        """Italic source line."""
        self.set_font("Carlito", "I", 9)
        self.cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def separator(self):
        """Horizontal rule."""
        y = self.get_y()
        self.set_draw_color(*SEPARATOR_COLOR)
        self.line(MARGIN_L, y, PAGE_W - MARGIN_R, y)
        self.ln(4)

    def add_course(self, code, name, au, ects, semester, objectives, topics, workload, materials, source):
        """Add a complete course description block."""
        # Each course starts on its own page (matching original layout)
        self.add_page()

        self.course_heading(f"{code}: {name}")
        self.course_meta(f"{au} AU ({ects} ECTS)", semester)

        self.sub_heading("Course Objectives")
        self.body_text(objectives)

        self.sub_heading("Main Topics Treated")
        self.body_text(topics)

        self.sub_heading("Workload")
        self.body_text(workload)

        self.sub_heading("Course Materials")
        self.body_text(materials)

        self.source_line(f"Source: {source}")
        self.separator()


def build_pdf():
    pdf = CourseDescriptionPDF()
    pdf.add_page()

    # ── Title ────────────────────────────────────────────────────────────────
    pdf.set_font("Carlito", "", 20)
    pdf.set_text_color(*TITLE_COLOR)
    pdf.cell(0, 10, "Course Descriptions: Quantitative Methods", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ── NEW Introduction Paragraph (EUR-tailored) ────────────────────────────
    pdf.set_text_color(*BLACK)
    pdf.set_font("Carlito", "", 10)

    # Use markdown=True in multi_cell for justified text with inline bold
    intro_text = (
        f"This document provides detailed course descriptions for all quantitative courses "
        f"completed by **Benjamin Oliver Yick** during his Bachelor of Computing (Hons) in Data Science and "
        f"Artificial Intelligence at **Nanyang Technological University, Singapore**. It is submitted to the "
        f"Erasmus School of Economics at Erasmus University Rotterdam as direct evidence of the **sufficient "
        f"mathematical background** required for admission to the **Pre-Master Econometrics and Management "
        f"Science Program (NL)**. As stipulated by the Examination Board at the Erasmus School of Economics, "
        f"applicants are required to demonstrate a solid foundation in advanced mathematics, applied statistics, "
        f"and quantitative analysis by uploading course descriptions and literature lists of equivalent courses "
        f"they have passed. The content herein, including course objectives, main topics treated, workload, and "
        f"prescribed literature, documents the comprehensive competencies acquired across nine university{MINUS}level "
        f"quantitative courses totaling 62 ECTS, spanning calculus, linear algebra, discrete mathematics, "
        f"probability theory, mathematical statistics, data analysis, survey sampling, and operations research. "
        f"These competencies align directly with the preparatory requirements in the Mathematics, Statistics, "
        f"and Operations Research clusters of the BSc in Econometrics and Operations Research at the Erasmus "
        f"School of Economics, against which the Examination Board benchmarks all applications."
    )
    pdf.multi_cell(CONTENT_W, 5, intro_text, align="J", markdown=True)
    pdf.ln(4)

    # ── Overview of quantitative courses ─────────────────────────────────────
    pdf.section_title("Overview of quantitative courses")

    # Table
    col_widths = [18, 65, 12, 14, 51]  # Code, Course, AU, ECTS, Semester
    headers = ["Code", "Course", "AU", "ECTS", "Semester"]

    courses_table = [
        ["BU5401", "Management Decision Tools", "3.0", "6", f"2024{MINUS}2025 Semester 1"],
        ["CS2400", "Foundation of Information Analytics", "3.0", "6", f"2024{MINUS}2025 Semester 2"],
        ["MH1805", "Calculus", "4.0", "8", f"2021{MINUS}2022 Semester 1"],
        ["MH1812", "Discrete Mathematics", "3.0", "6", f"2021{MINUS}2022 Semester 1"],
        ["MH2500", "Probability and Introduction to\nStatistics", "4.0", "8", f"2022{MINUS}2023 Semester 1"],
        ["MH2802", "Linear Algebra for Scientists", "3.0", "6", f"2022{MINUS}2023 Semester 1"],
        ["MH3500", "Statistics", "4.0", "8", f"2022{MINUS}2023 Semester 2"],
        ["MH3511", "Data Analysis with Computer", "3.0", "6", f"2022{MINUS}2023 Semester 2"],
        ["MH4511", "Sampling and Survey", "4.0", "8", f"2025{MINUS}2026 Semester 1"],
    ]

    # Header row
    pdf.set_font("Carlito", "B", 10)
    pdf.set_fill_color(*TABLE_HEADER_BG)
    pdf.set_draw_color(180, 180, 180)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, header, border=1, fill=True)
    pdf.ln()

    # Data rows
    pdf.set_font("Carlito", "", 10)
    for row in courses_table:
        # Calculate max height needed for this row
        max_lines = 1
        for i, cell_text in enumerate(row):
            lines = cell_text.count('\n') + 1
            if lines > max_lines:
                max_lines = lines

        row_height = 7 * max_lines

        for i, cell_text in enumerate(row):
            x = pdf.get_x()
            y = pdf.get_y()
            # Draw cell border
            pdf.rect(x, y, col_widths[i], row_height)
            # Write text inside cell
            if '\n' in cell_text:
                parts = cell_text.split('\n')
                for j, part in enumerate(parts):
                    pdf.set_xy(x + 1, y + 1 + j * 5)
                    pdf.cell(col_widths[i] - 2, 5, part)
            else:
                pdf.set_xy(x + 1, y + (row_height - 5) / 2)
                pdf.cell(col_widths[i] - 2, 5, cell_text)
            pdf.set_xy(x + col_widths[i], y)

        pdf.set_xy(MARGIN_L, pdf.get_y() + row_height)

    pdf.ln(4)

    # Note
    pdf.set_font("Carlito", "I", 9)
    note_text = f"Note: ECTS credits are calculated using the conversion rate of 1 NTU Academic Unit (AU) = 2 ECTS. NTU Academic Units include self{MINUS}study time within their calculation, whereas ECTS credits account for self{MINUS}study time separately."
    pdf.multi_cell(CONTENT_W, 4.5, note_text, align="J")
    pdf.ln(6)

    # ── Detailed course descriptions ─────────────────────────────────────────
    pdf.section_title("Detailed course descriptions")

    # ── Course 1: BU5401 ─────────────────────────────────────────────────────
    pdf.add_course(
        "BU5401", "Management Decision Tools",
        "3.0", "6", f"2024{MINUS}2025 Semester 1",
        "This course aims to develop the use of a scientific approach using mathematical methods and computer software to make managerial decisions. Upon successful completion, students should be able to recognise the characteristics of problems for which quantitative analysis may be appropriate, formulate a real-world problem in mathematical terms, select an appropriate quantitative model and apply it to the formulated problem, use computer software to solve the mathematical model, and interpret the results of the quantitative analysis to make management decisions.",
        "Optimisation models for business decisions; Simulation; Inventory control; Waiting line management (queueing theory); Forecasting; Decision making under uncertainty.",
        "39 contact hours over 13 weeks (3 hours per week comprising lectures and tutorials).",
        f"Textbook: Anderson, D.R., Sweeney, D.J., Williams, T.A. and Martin, R.K. (2016), An Introduction to Management Science, 14th Edition, Cengage Learning (ISBN{MINUS}13: 978{MINUS}1{MINUS}111{MINUS}82361{MINUS}0). Other References: Chin, C.K. (2016), Essential Basics of Probability, Statistics and Analytics, 1st Edition, SoftML (ISBN{MINUS}13: 978{MINUS}981{MINUS}11{MINUS}0335{MINUS}3); Taylor, B.W. III (2012), Introduction to Management Science: Global Edition, 11th Edition, Pearson (ISBN{MINUS}13: 9780273766407); Hillier, F.S. and Hillier, M.S. (2008), Introduction to Management Science: A Modeling and Case Studies Approach with Spreadsheets, 3rd Edition, McGraw{MINUS}Hill Irwin (ISBN{MINUS}13: 978{MINUS}0{MINUS}07{MINUS}312903{MINUS}7).",
        "NTU Nanyang Business School OBTL+ Syllabus"
    )

    # ── Course 2: CS2400 ─────────────────────────────────────────────────────
    pdf.add_course(
        "CS2400", "Foundation of Information Analytics",
        "3.0", "6", f"2024{MINUS}2025 Semester 2",
        "This course introduces the statistical foundations of data science and information analytics for handling massive databases. It covers the statistical concepts required for big data analytics and introduces students to statistical tests and statistical modelling.",
        "Importance of Statistics; Descriptive Statistics; Probability; Counting Techniques; Discrete Probability Distributions; Normal Distribution; Confidence Intervals; Hypothesis Testing for One Population; Hypothesis Testing for Two Populations; Correlation and Linear Regression; Non-linear Regression; Application of Statistics in Information Analytics.",
        "2 hours 40 minutes of lectures plus 1 hour of tutorials per week, over 13 weeks. Total approximately 48 contact hours per semester.",
        f"Study Guide, 8th Edition: a free e-book in PDF format compiled from twelve statistics textbooks (provided by the instructor). The New Cambridge Statistical Tables (NCST), 2nd Edition: compilation of statistical tables for hypothesis tests. Reference Books: Agresti, A. and Franklin, C. (2013), Statistics: The Art and Science of Learning from Data, 3rd Edition, Pearson Education; Johnson, R. and Kuby, P. (2012), Elementary Statistics, 11th Edition, Brooks/Cole; Utts, J.M. and Heckard, R.F. (2015), Mind on Statistics, 5th Edition, Cengage Learning; Montgomery, D.C., Runger, G.C. and Hubele, N.F. (2001), Engineering Statistics, 2nd Edition, John Wiley and Sons.",
        "NTU WKWSCI Course Outline (AY2024/25)"
    )

    # ── Course 3: MH1805 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH1805", "Calculus",
        "4.0", "8", f"2021{MINUS}2022 Semester 1",
        "This course aims to equip students with the subject knowledge, logical reasoning, and analytical skills to apply the concepts and techniques of calculus of one variable to solve problems in science. Upon completion, students will be able to independently process and interpret concepts related to differentiation, integration, power series, and ordinary differential equations; critically assess the applicability of mathematical tools; critically assess the validity of mathematical arguments; and present mathematical ideas logically and coherently.",
        "Sets and functions; Limits and continuity, one-to-one and inverse functions; Differentiation and optimization; Definition of Riemann Integral, Fundamental Theorem of Calculus, applications of integration; Methods of integration; Elementary theory and methods of Ordinary Differential Equations; Series, Power Series, Taylor Series.",
        "32 in-class lecture hours and 30 hours of recorded lectures, plus 2 hours of tutorials per week for 12 weeks. Total approximately 62 contact hours over one semester.",
        f"Calculus by Michael Spivak (ISBN: 978{MINUS}0{MINUS}914098{MINUS}91{MINUS}1).",
        "NTU SPMS OBTL Document"
    )

    # ── Course 4: MH1812 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH1812", "Discrete Mathematics",
        "3.0", "6", f"2021{MINUS}2022 Semester 1",
        f"This course serves as an introduction to various topics in discrete mathematics. The main aim is to learn topics from number theory, logic, combinatorics, and graph theory. It provides students with a solid mathematical foundation and is intended for first{MINUS}year computer science and computer engineering students. Upon completion, students should be able to: identify congruent integers modulo a positive integer; formulate, interpret, and manipulate logical statements; identify valid and invalid arguments; prove elementary mathematical results using various proof techniques; apply basic counting tools; solve linear recurrence relations; manipulate relations and functions between sets; and apply basic techniques in graph theory.",
        "Elementary Number Theory (types of numbers, Euclidean division, modular arithmetic); Propositional Logic (propositions, logical operators, truth tables, De Morgan\u2019s laws); Predicate Logic (predicates, quantification, negating quantifiers); Proof Techniques (direct proof, proof by contradiction, proof by contrapositive); Combinatorics (principle of counting, combinations, permutations); Linear Recurrence Relations; Set Theory (sets, union, intersection, set difference, cardinality, power sets, Cartesian products); Relations (reflexivity, symmetry, antisymmetry, transitivity, equivalence relations, partial orders); Functions (injectivity, surjectivity, bijectivity, inverse, pigeonhole principle, countable sets); Graph Theory (vertices, edges, subgraphs, Euler paths/cycles, Hamilton cycles, graph isomorphism).",
        "2 hours of lectures plus 1 hour of tutorials per week, over 13 weeks. Total 38 contact hours per semester.",
        f"1. Epp, S.S. (2010), Discrete Mathematics with Applications, 4th Edition, Thomson Learning (ISBN{MINUS}10: 0495391328). 2. Rosen, K.H. (2007), Discrete Mathematics and Its Applications, 6th Edition, McGraw{MINUS}Hill (ISBN{MINUS}10: 0072880082).",
        "NTU SPMS OBTL Document"
    )

    # ── Course 5: MH2500 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH2500", "Probability and Introduction to Statistics",
        "4.0", "8", f"2022{MINUS}2023 Semester 1",
        f"This is a core mathematical course aiming to develop understanding of fundamental concepts in probability such as random variables, independence, basic probability distributions, conditional expectations and conditional variances, the law of large numbers, and the central limit theorem with applications. The course also prepares students for further courses in probability and statistics (MH3500, MH3512). Upon completion, students will be able to: calculate probabilities of events concerning discrete distributions by counting; calculate conditional probabilities with Bayes\u2019 Theorem; describe probability distributions using CDF/PDF; identify appropriate probability distributions for modelling; calculate expectation, variance, MGF, and quantiles; calculate distributions of functions of random variables and covariance; prove or disprove independence of random variables; calculate conditional expectations and variances; and apply the central limit theorem.",
        "Events, probabilities, law of total probability, Bayes\u2019 theorem; Independence of events; Discrete distributions (binomial, hypergeometric, Poisson); Continuous distributions (normal, exponential) and densities; Joint distribution, marginal and conditional distributions for discrete and continuous variables; Functions of two or more random variables, order statistics; Expectation and variance; Covariance and correlation coefficient; Markov and Chebyshev inequalities; Conditional expectations, conditional variances, and moment generating functions; Law of large numbers; Central limit theorem with applications.",
        "3 hours of lectures plus 1 hour of tutorials per week, over 13 weeks. Total 51 contact hours per semester.",
        f"Ross, S. (2020), A First Course in Probability, 10th Edition, Pearson (ISBN: 978{MINUS}0134753119).",
        "NTU SPMS OBTL Document"
    )

    # ── Course 6: MH2802 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH2802", "Linear Algebra for Scientists",
        "3.0", "6", f"2022{MINUS}2023 Semester 1",
        "This course aims to support students in acquiring a wider range of mathematical concepts related to vector spaces and linear algebra, while developing a strong set of mathematical skills for upper-level Physical, Computing, and Data Science courses. Through a mathematical approach to problem-solving, students will develop thinking, reasoning, communication, and modelling skills. The course connects ideas within mathematics and applies mathematical principles in the context of physics, computing, and data science, with special emphasis on recent technological advances such as machine learning and quantum computing.",
        "Vector Algebra and Analytical Geometry; Linear Spaces (axioms, subspaces, basis, dimension); Linear Transformations and Matrices (matrix operations, rank, null space); Eigenvalues and Eigenvectors (characteristic polynomial, diagonalisation); Applications of Linear Algebra to problems in Physical and Computing Science (including machine learning and quantum computing applications).",
        "2 hours of lectures plus 1 hour of tutorials per week, over 13 weeks. Total 38 contact hours per semester.",
        f"Lay, D.C., Lay, S.R. and McDonald, J.J. (2021), Linear Algebra and Its Applications, Global Edition, 6th Edition, Pearson (ISBN{MINUS}13: 978{MINUS}1292351216).",
        "NTU SPMS OBTL Document"
    )

    # ── Course 7: MH3500 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH3500", "Statistics",
        "4.0", "8", f"2022{MINUS}2023 Semester 2",
        f"This course develops understanding of the statistical concepts of parameter estimation and hypothesis testing that are fundamental for real-life applications of statistics. Upon completion, students will be able to: apply basic probability concepts (PMF, PDF, CDF, expected values, variance, moments) in a statistical context; use standard probability distributions to model statistical scenarios; explain the relevance of the Central Limit Theorem for statistics; construct parameter estimators using maximum likelihood and method of moments; rigorously assess the quality of estimators; analyse asymptotic properties of estimators; construct exact and approximate confidence intervals; explain the purpose and philosophy of hypothesis testing and the meaning of p{MINUS}values; create and apply hypothesis tests; compute the size and power of a test; and construct most powerful tests using the Neyman-Pearson Lemma.",
        f"Review of probability; Random samples, sample mean and sample variance; Distributions derived from the normal distribution; Central Limit Theorem and its significance for statistics; Introduction to parameter estimation and quality criteria for estimators; Constructing good estimators: method of moments and maximum likelihood method; Asymptotic properties of estimators, Cram\u00e9r-Rao bound and efficient estimators; Confidence intervals for estimators; Introduction to hypothesis testing and Fisher{MINUS}type tests; Neyman-Pearson tests and Neyman-Pearson Lemma.",
        "3 hours of lectures plus 1 hour of tutorials per week, over 13 weeks. Total 52 contact hours per semester.",
        f"1. Rice, J.A., Mathematical Statistics and Data Analysis, 3rd Edition (ISBN{MINUS}13: 978{MINUS}8131519547). 2. Hogg, R.V., McKean, J.W. and Craig, A.T., Introduction to Mathematical Statistics, 8th Edition, Pearson. 3. Casella, G. and Berger, R.L., Statistical Inference, 2nd Edition, Thomson Press.",
        "NTU SPMS OBTL Document"
    )

    # ── Course 8: MH3511 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH3511", "Data Analysis with Computer",
        "3.0", "6", f"2022{MINUS}2023 Semester 2",
        "This course provides basic concepts for data analysis using the R programming language. Students will learn the skills of plotting, summarising, making inferences, and presenting various types of data. Upon completion, students will be able to evaluate mathematical functions using R, distinguish between measurement scales, explain statistical quantities, construct various plots, perform statistical inference, understand error types in hypothesis testing, analyse categorical data, use parametric methods, and perform linear regression.",
        f"Basics of R Programming (syntax, mathematical expressions, variables, vectors, matrices, dataframes, importing and subsetting data, loops); Describing Data (mean, median, standard deviation, variance, inter{MINUS}quartile range, boxplot, histogram, stem{MINUS}leaf plot, normality checks, QQ{MINUS}plot, outliers, transformation); Statistical Inference (sampling distribution, Central Limit Theorem, confidence intervals, hypothesis testing, Type I and Type II errors, p{MINUS}values); Categorical Data (proportion estimation, testing of proportion parameter, goodness{MINUS}of{MINUS}fit test, two{MINUS}way contingency table, paired contingency table); Multiple Samples (two independent samples, inference on mean difference, two dependent samples, ANOVA test, multiple dependent samples); Nonparametric Tests (quantile test, Wilcoxon rank{MINUS}sum test, Kruskal-Wallis test, sign test, Wilcoxon signed{MINUS}rank test, Friedman test); Correlation and Regression (correlation coefficient, confidence intervals, simple linear regression model, inference on parameters, prediction inference, model checking).",
        "Approximately 50 contact hours over 13 weeks, comprising lectures and computer laboratory sessions.",
        f"1. Hothorn, T. and Everitt, B.S. (2014), A Handbook of Statistical Analysis Using R, 3rd Edition, CRC Press (ISBN{MINUS}10: 1482204584; ISBN{MINUS}13: 978{MINUS}1482204582). 2. Crawley, M.J. (2005), Statistics: An Introduction Using R, Wiley (ISBN{MINUS}10: 0470022981; ISBN{MINUS}13: 978{MINUS}0470022986).",
        "NTU SPMS OBTL Document"
    )

    # ── Course 9: MH4511 ─────────────────────────────────────────────────────
    pdf.add_course(
        "MH4511", "Sampling and Survey",
        "4.0", "8", f"2025{MINUS}2026 Semester 1",
        "This course gives an introduction to the statistical aspects of taking and analysing a sample. Students will learn to determine the appropriate sampling design in various situations, use the correct method for analysis, and interpret the results. Upon completion, students will be able to: recognise and describe various sampling designs; compute estimates for population mean, proportion, and total; construct confidence intervals for population parameters; apply ratio and regression estimations to improve accuracy of estimates; determine the required sample size and its allocation under given conditions; and explain the importance of nonresponse and apply techniques to reduce nonresponse rates.",
        "Probability Sampling (types of probability samples, simple random sampling, estimation of population mean/proportion/total, sample size estimation, systematic sampling); Stratified Sampling (theory, sampling weights, estimation, allocating observations to strata, sample size estimation, defining strata, post-stratification); Ratio and Regression Estimations (ratio estimation, regression estimation, selecting sample size, relative efficiency of estimators); Cluster Sampling (one-stage and two-stage cluster sampling, estimation, selecting sample size, cluster sampling with probability proportional to size); Sampling with Unequal Probabilities (one-stage and two-stage sampling with replacement, unequal-probability sampling without replacement); Nonresponse (effects of ignoring nonresponse, callbacks and two-phase sampling, weighting methods for nonresponse, imputation).",
        "Total 52 contact hours over 13 weeks, consisting of lectures, tutorials, and assignments.",
        f"1. Lohr, S.L. (2010), Sampling: Design and Analysis, 2nd Edition, Brooks/Cole (ISBN: 978{MINUS}0495105275). 2. Scheaffer, R.L. et al. (2012), Elementary Survey Sampling, 7th Edition, Brooks/Cole (ISBN: 978{MINUS}0840053619).",
        "NTU SPMS OBTL Document"
    )

    # ── Save ─────────────────────────────────────────────────────────────────
    pdf.output(OUTPUT_PATH)
    print(f"PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
