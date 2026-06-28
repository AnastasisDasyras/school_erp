import inspect
from app.modules.students.domain.student import Student

print('--- signature ---')
print(inspect.signature(Student.__init__))

print()
print('--- source (if available) ---')
try:
    print(inspect.getsource(Student.__init__))
except (OSError, TypeError) as e:
    print(f'no source available: {e}')


