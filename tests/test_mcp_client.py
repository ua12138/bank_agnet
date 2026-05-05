"""模块说明：该文件用于承载项目中的相关实现。"""

from __future__ import annotations

import unittest

from hz_bank_aiops.mcp import RagMCPClient


class RagMCPClientTestCase(unittest.TestCase):
    """RagMCPClientTestCase：封装该领域职责，供上层流程统一调用。"""
    def test_health_error_handled(self) -> None:
        """test_health_error_handled：测试意图是验证该场景下的行为与预期结果一致。"""
        client = RagMCPClient(base_url="http://127.0.0.1:65530", timeout_sec=0.2)
        res = client.health()
        self.assertFalse(res.ok)
        self.assertIsInstance(res.error, str)

    def test_query_error_handled(self) -> None:
        """test_query_error_handled：测试意图是验证该场景下的行为与预期结果一致。"""
        client = RagMCPClient(base_url="http://127.0.0.1:65530", timeout_sec=0.2)
        res = client.query(kb_id="kb", query="q", top_k=1)
        self.assertFalse(res.ok)
        self.assertIsInstance(res.error, str)


if __name__ == "__main__":
    unittest.main()

