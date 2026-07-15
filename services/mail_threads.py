import re


SUBJECT_PREFIX_RE = re.compile(
    r"^(re|fwd|fw|yanit|yanıt|cevap|ilet|aw)\s*:\s*",
    re.I,
)


def normalize_subject(subject):
    value = (subject or "").strip()
    while True:
        cleaned = SUBJECT_PREFIX_RE.sub("", value).strip()
        if cleaned == value:
            break
        value = cleaned
    return value.lower()


def _has_reply_marker(subject):
    return bool(SUBJECT_PREFIX_RE.match((subject or "").strip()))


def _mail_reference_ids(mail):
    refs = []
    for value in mail.get("reference_ids") or []:
        norm = (value or "").strip().lower()
        if norm and norm not in refs:
            refs.append(norm)

    message_id = (mail.get("message_id") or "").strip().lower()
    if message_id and message_id not in refs:
        refs.append(message_id)

    in_reply_to = (mail.get("in_reply_to") or "").strip().lower()
    if in_reply_to and in_reply_to not in refs:
        refs.append(in_reply_to)

    return refs


class _UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, index):
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left, right):
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def build_conversation_key(mail):
    thread_id = (mail.get("thread_id") or "").strip()
    if thread_id:
        return f"thread:{thread_id}"

    message_id = (mail.get("message_id") or "").strip().lower()
    if message_id:
        return f"msg:{message_id}"

    subject = normalize_subject(mail.get("subject", ""))
    return f"conv:{subject}"


def _sort_messages(messages):
    return sorted(
        messages,
        key=lambda mail: mail.get("date_ts", 0),
        reverse=True,
    )


def group_mails_by_thread(mailler):
    if not mailler:
        return []

    if len(mailler) == 1:
        mail = mailler[0]
        return [{
            **mail,
            "thread_id": mail.get("thread_id") or build_conversation_key(mail),
            "thread_ids": [mail["id"]],
            "thread_count": 1,
            "thread_messages": [mail],
        }]

    union = _UnionFind(len(mailler))
    message_id_to_index = {}

    for index, mail in enumerate(mailler):
        message_id = (mail.get("message_id") or "").strip().lower()
        if message_id:
            message_id_to_index[message_id] = index

    gmail_groups = {}
    for index, mail in enumerate(mailler):
        gmail_thread_id = (mail.get("thread_id") or "").strip()
        if gmail_thread_id:
            gmail_groups.setdefault(gmail_thread_id, []).append(index)

    for indices in gmail_groups.values():
        first = indices[0]
        for other in indices[1:]:
            union.union(first, other)

    for index, mail in enumerate(mailler):
        for ref in _mail_reference_ids(mail):
            parent_index = message_id_to_index.get(ref)
            if parent_index is not None:
                union.union(index, parent_index)

    subject_groups = {}
    for index, mail in enumerate(mailler):
        subject_key = normalize_subject(mail.get("subject", ""))
        if subject_key:
            subject_groups.setdefault(subject_key, []).append(index)

    for indices in subject_groups.values():
        if len(indices) < 2:
            continue

        should_merge = False
        for index in indices:
            mail = mailler[index]
            if _mail_reference_ids(mail):
                should_merge = True
                break
            if _has_reply_marker(mail.get("subject")):
                should_merge = True
                break

        if not should_merge:
            continue

        first = indices[0]
        for other in indices[1:]:
            union.union(first, other)

    grouped_map = {}
    order = []
    for index, mail in enumerate(mailler):
        root = union.find(index)
        if root not in grouped_map:
            grouped_map[root] = []
            order.append(root)
        grouped_map[root].append(mail)

    grouped = []
    for root in order:
        messages = _sort_messages(grouped_map[root])
        primary = messages[0]
        thread_ids = [mail["id"] for mail in messages]
        conversation_key = build_conversation_key(primary)

        grouped.append({
            **primary,
            "thread_id": primary.get("thread_id") or conversation_key,
            "thread_ids": thread_ids,
            "thread_count": len(messages),
            "thread_messages": messages,
        })

    return grouped


def expand_selected_mail_ids(mailler, selected_ids):
    selected_set = {str(mail_id).strip() for mail_id in selected_ids if str(mail_id).strip()}
    if not selected_set or not mailler:
        return list(selected_set)

    expanded = []
    seen = set()
    for mail in mailler:
        thread_ids = mail.get("thread_ids") or [mail.get("id")]
        if mail.get("id") not in selected_set and not any(
            tid in selected_set for tid in thread_ids
        ):
            continue
        for mail_id in thread_ids:
            if mail_id and mail_id not in seen:
                seen.add(mail_id)
                expanded.append(mail_id)

    return expanded or list(selected_set)
