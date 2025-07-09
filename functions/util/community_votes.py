"""コミュニティ投票集計のユーティリティモジュール"""

from typing import List

from type.cosmos import QuestionDiscussion


def calculate_community_votes(discussions: List[QuestionDiscussion]) -> List[str]:
    """
    コミュニティのディスカッションからユーザーが選択した選択肢を集計し、
    コミュニティでの回答の割合の文字列配列を生成する

    Args:
        discussions (List[QuestionDiscussion]): コミュニティのディスカッション

    Returns:
        List[str]: コミュニティでの回答の割合の文字列配列(例：["A (60%)", "B (40%)"]、ユーザーが選択した選択肢がすべてNoneの場合は空配列)
    """

    # ユーザーが選択した選択肢(selectedAnswer)を集計
    answer_counts = {}
    total_votes = 0
    for discussion in discussions:
        selected_answer = discussion.get("selectedAnswer")
        if selected_answer:
            answer_counts[selected_answer] = answer_counts.get(selected_answer, 0) + 1
            total_votes += 1

    if total_votes == 0:
        return []

    # 割合を計算してコミュニティでの回答の割合の文字列配列を生成
    community_votes = []
    for answer, count in sorted(answer_counts.items()):
        percentage = round((count / total_votes) * 100)
        community_votes.append(f"{answer} ({percentage}%)")

    return community_votes
