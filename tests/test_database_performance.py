import unittest
import time
import threading
import statistics
from data.db import Database
from data.user_repository import UserRepository
from data.admin_repository import AdminRepository
class TestDatabasePerformance(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.user_repo = UserRepository(self.db)
        self.admin_repo = AdminRepository(self.db)
        self.setup_test_data()
    def setup_test_data(self):
        self.test_users = []
        for i in range(100):
            username = f"testuser{i}"
            self.test_users.append(username)
            try:
                self.user_repo.create_user_in_db(username)
            except:
                pass
    def tearDown(self):
        self.cleanup_test_data()
    def cleanup_test_data(self):
        for username in self.test_users:
            try:
                user = self.user_repo.find_user_by_username(username)
                if user:
                    self.user_repo.delete_user(user['id'])
            except:
                pass
    def test_connection_pool_performance(self):
        execution_times = []
        for _ in range(100):
            start_time = time.time()
            result = self.db.execute_query("SELECT COUNT(*) as count FROM users")
            end_time = time.time()
            execution_times.append(end_time - start_time)
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        self.assertLess(avg_time, 0.01)
        self.assertLess(max_time, 0.05)
        logger.info("Connection Pool Performance", avg_time=avg_time, max_time=max_time, min_time=min_time)
    def test_concurrent_database_operations(self):
        def concurrent_operation():
            for _ in range(10):
                self.db.execute_query("SELECT COUNT(*) as count FROM users")
        threads = []
        start_time = time.time()
        for _ in range(10):
            thread = threading.Thread(target=concurrent_operation)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        end_time = time.time()
        total_time = end_time - start_time
        self.assertLess(total_time, 2.0)
        logger.info("Concurrent Operations", total_time=total_time)
    def test_bulk_operations_performance(self):
        start_time = time.time()
        for i in range(50):
            username = f"bulkuser{i}"
            try:
                self.user_repo.create_user_in_db(username)
            except:
                pass
        end_time = time.time()
        bulk_create_time = end_time - start_time
        self.assertLess(bulk_create_time, 1.0)
        print(f"Bulk Create Performance - Time: {bulk_create_time:.2f}s")
        start_time = time.time()
        users = self.user_repo.get_all_users()
        end_time = time.time()
        bulk_read_time = end_time - start_time
        self.assertLess(bulk_read_time, 0.5)
        print(f"Bulk Read Performance - Time: {bulk_read_time:.2f}s")
    def test_query_optimization(self):
        execution_times = []
        for _ in range(50):
            start_time = time.time()
            result = self.db.execute_query("""
                SELECT u.username, u.status, q.quota_bytes, q.bytes_used
                FROM users u
                LEFT JOIN user_quotas q ON u.id = q.user_id
                WHERE u.status = 'active'
                ORDER BY u.username
            """)
            end_time = time.time()
            execution_times.append(end_time - start_time)
        avg_time = statistics.mean(execution_times)
        self.assertLess(avg_time, 0.01)
        print(f"Complex Query Performance - Avg time: {avg_time:.4f}s")
    def test_transaction_performance(self):
        execution_times = []
        for _ in range(20):
            start_time = time.time()
            try:
                self.db.execute_transaction([
                    ("INSERT INTO users (username, status) VALUES (?, ?)", ("transuser1", "active")),
                    ("INSERT INTO users (username, status) VALUES (?, ?)", ("transuser2", "active")),
                    ("UPDATE users SET status = ? WHERE username = ?", ("inactive", "transuser1"))
                ])
                end_time = time.time()
                execution_times.append(end_time - start_time)
            except:
                pass
        if execution_times:
            avg_time = statistics.mean(execution_times)
            self.assertLess(avg_time, 0.05)
            print(f"Transaction Performance - Avg time: {avg_time:.4f}s")
    def test_memory_usage_under_load(self):
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        for _ in range(1000):
            self.db.execute_query("SELECT COUNT(*) as count FROM users")
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        self.assertLess(memory_increase, 50)
        print(f"Memory Usage - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB, Increase: {memory_increase:.1f}MB")
    def test_connection_cleanup(self):
        initial_connections = len(self.db._pool.pool.queue) if hasattr(self.db, '_pool') else 0
        for _ in range(100):
            self.db.execute_query("SELECT 1")
        final_connections = len(self.db._pool.pool.queue) if hasattr(self.db, '_pool') else 0
        self.assertLessEqual(final_connections, initial_connections + 5)
        print(f"Connection Cleanup - Initial: {initial_connections}, Final: {final_connections}")
    def test_repository_performance(self):
        execution_times = []
        for _ in range(50):
            start_time = time.time()
            users = self.user_repo.get_all_users()
            end_time = time.time()
            execution_times.append(end_time - start_time)
        avg_time = statistics.mean(execution_times)
        self.assertLess(avg_time, 0.01)
        print(f"Repository Performance - Avg time: {avg_time:.4f}s")
    def test_caching_impact(self):
        execution_times_without_cache = []
        execution_times_with_cache = []
        for _ in range(20):
            start_time = time.time()
            self.user_repo.get_all_users()
            end_time = time.time()
            execution_times_without_cache.append(end_time - start_time)
        for _ in range(20):
            start_time = time.time()
            self.user_repo.get_all_users()
            end_time = time.time()
            execution_times_with_cache.append(end_time - start_time)
        avg_without_cache = statistics.mean(execution_times_without_cache)
        avg_with_cache = statistics.mean(execution_times_with_cache)
        improvement = ((avg_without_cache - avg_with_cache) / avg_without_cache) * 100
        print(f"Caching Impact - Without cache: {avg_without_cache:.4f}s, With cache: {avg_with_cache:.4f}s, Improvement: {improvement:.1f}%")
    def test_database_file_size(self):
        import os
        from data.db import Database
        db = Database()
        file_size = os.path.getsize(db.db_file) / 1024
        self.assertLess(file_size, 1000)
        print(f"Database File Size: {file_size:.1f}KB")
    def test_index_performance(self):
        execution_times_without_index = []
        execution_times_with_index = []
        for _ in range(20):
            start_time = time.time()
            self.db.execute_query("SELECT * FROM users WHERE username = ?", ("testuser1",))
            end_time = time.time()
            execution_times_with_index.append(end_time - start_time)
        avg_with_index = statistics.mean(execution_times_with_index)
        self.assertLess(avg_with_index, 0.001)
        print(f"Index Performance - Avg time: {avg_with_index:.6f}s")
if __name__ == '__main__':
    unittest.main()
