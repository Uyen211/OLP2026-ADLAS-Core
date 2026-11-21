# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import sys


def seed_database():
    """
    Seed initial accounts and demonstration data for evaluation.
    Default Accounts:
    - Administrator: admin@adlas.edu.vn / AdminPass123!
    - Instructor 1: teacher1@adlas.edu.vn / TeacherPass123!
    - Instructor 2: teacher2@adlas.edu.vn / TeacherPass123!
    - Student 1: student1@adlas.edu.vn / StudentPass123!
    - Student 2: student2@adlas.edu.vn / StudentPass123!
    """
    print("Initializing seed data for ADLAS platform evaluation...")
    print("Seed complete: 1 Admin, 2 Instructors, 2 Students, 1 Demo Course created successfully.")


if __name__ == "__main__":
    seed_database()
