"""
Quick script to sanity-check cohort naming for collisions.

Usage:
    python scripts/test_cohort_naming.py
"""
from analytics.ai_service import generate_cohort_name, ISSUE_EXAMPLES


def test_cases():
    return [
        {
            "bounce": 75,
            "duration": 15,
            "depth": 1.2,
            "top_goals": "apply_it_button(6%)",
            "top_interests": "рейтинги (40%)",
            "interest_codes": ["rating", "admission"],
        },
        {
            "bounce": 30,
            "duration": 120,
            "depth": 5,
            "top_goals": "it_master_form(12%), contacts_view(7%)",
            "top_interests": "программы (50%), формы (20%)",
            "interest_codes": ["programs", "forms"],
        },
        {
            "bounce": 50,
            "duration": 60,
            "depth": 3,
            "top_goals": "contacts_view(8%)",
            "top_interests": "контакты (60%)",
            "interest_codes": ["contacts"],
        },
        {
            "bounce": 65,
            "duration": 25,
            "depth": 2,
            "top_goals": "None",
            "top_interests": "новости (55%)",
            "interest_codes": ["news"],
        },
        {
            "bounce": 20,
            "duration": 200,
            "depth": 6,
            "top_goals": "b24_form_2_end(10%), it_master_form(5%)",
            "top_interests": "формы (70%), поступление (20%)",
            "interest_codes": ["forms", "admission"],
        },
    ]


def main():
    seen = {}
    duplicates = []
    for idx, metrics in enumerate(test_cases(), start=1):
        name = generate_cohort_name(metrics)
        print(f"[{idx}] {name}  --  metrics={metrics}")
        if name in seen:
            duplicates.append((name, seen[name], idx))
        else:
            seen[name] = idx

    if duplicates:
        print("\nDuplicates detected:")
        for name, first_idx, dup_idx in duplicates:
            print(f"  '{name}' for cases {first_idx} and {dup_idx}")
    else:
        print("\nNo duplicate names detected across test cases.")


if __name__ == "__main__":
    print("Issue type examples:", ISSUE_EXAMPLES)
    main()
