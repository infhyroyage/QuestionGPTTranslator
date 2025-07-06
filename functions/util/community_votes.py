"""コミュニティ投票集計のユーティリティモジュール"""

from typing import List, Optional
from type.cosmos import QuestionDiscussion


def calculate_community_votes(
        discussions: Optional[List[QuestionDiscussion]]
) -> Optional[List[str]]:
    """
    discussions配列からselectedAnswerを集計してcommunityVotes形式の文字列配列を生成する

    Args:
        discussions (Optional[List[QuestionDiscussion]]): ディスカッション配列

    Returns:
        Optional[List[str]]: communityVotes形式の文字列配列（例：["A (60%)", "B (40%)"]）
                            discussionsがNoneまたは空の場合はNone
    """

    if not discussions:
        return None

    # selectedAnswerを集計
    answer_counts = {}
    total_votes = 0

    for discussion in discussions:
        selected_answer = discussion.get("selectedAnswer")
        if selected_answer:
            answer_counts[selected_answer] = answer_counts.get(selected_answer, 0) + 1
            total_votes += 1

    if total_votes == 0:
        return None

    # 割合を計算してcommunityVotes形式の文字列配列を生成
    community_votes = []
    for answer, count in sorted(answer_counts.items()):
        percentage = round((count / total_votes) * 100)
        community_votes.append(f"{answer} ({percentage}%)")

    return community_votes if community_votes else None