---
                title: {{ title }}
                created_at: {{ created_at }}
                updated_at: {{ updated_at }}
                {% if tags %}tags:
                {% for tag in tags %}  - {{ tag }}
                {% endfor %}{% endif %}
                {% if category %}category: {{ category }}
                {% endif %}{% if linked_notes %}linked_notes:
                {% for link in linked_notes %}  - {{ link }}
                {% endfor %}{% endif %}type: project_ideas
                ---

                # {{ title }}

                ## Section 1

                Content for section 1...

                ## Section 2

                Content for section 2...

                {% if linked_notes %}
                ## Related Notes

                {% for link in linked_notes %}* [[{{ link }}]]
                {% endfor %}
                {% endif %}
                