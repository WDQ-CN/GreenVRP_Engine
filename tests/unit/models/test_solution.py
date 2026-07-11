"""
单元测试：models/solution.py — Solution ORM 模型 CRUD
"""

from datetime import datetime, timezone

import pytest

from models.solution import Solution


class TestSolutionCRUD:
    def test_create_solution(self, fresh_db):
        solution = Solution(
            scenario_id=1,
            job_id="test-job-001",
            status="completed",
            total_distance=100.5,
            total_cost=1500.0,
            carbon_emission_kg=25.5,
            solve_time_seconds=5.2,
        )
        fresh_db.add(solution)
        fresh_db.commit()

        saved = fresh_db.query(Solution).filter_by(job_id="test-job-001").first()
        assert saved is not None
        assert saved.total_cost == 1500.0
        assert saved.total_distance == 100.5

    def test_read_solution(self, fresh_db):
        solution = Solution(scenario_id=1, job_id="job-002", status="pending")
        fresh_db.add(solution)
        fresh_db.commit()

        found = fresh_db.query(Solution).filter_by(job_id="job-002").first()
        assert found is not None
        assert found.status == "pending"

    def test_update_solution_status(self, fresh_db):
        solution = Solution(scenario_id=1, job_id="job-003", status="pending")
        fresh_db.add(solution)
        fresh_db.commit()

        solution.status = "completed"
        fresh_db.commit()

        updated = fresh_db.query(Solution).filter_by(job_id="job-003").first()
        assert updated.status == "completed"

    def test_delete_solution(self, fresh_db):
        solution = Solution(scenario_id=1, job_id="job-004")
        fresh_db.add(solution)
        fresh_db.commit()

        fresh_db.delete(solution)
        fresh_db.commit()

        deleted = fresh_db.query(Solution).filter_by(job_id="job-004").first()
        assert deleted is None

    def test_is_completed(self):
        solution = Solution(scenario_id=1, job_id="job-005", status="completed")
        assert solution.is_completed() is True
        assert solution.is_failed() is False

    def test_is_failed(self):
        solution = Solution(scenario_id=1, job_id="job-006", status="failed")
        assert solution.is_failed() is True
        assert solution.is_completed() is False

    def test_solution_repr(self):
        solution = Solution(job_id="job-007", status="completed")
        assert "job-007" in repr(solution)
        assert "completed" in repr(solution)
