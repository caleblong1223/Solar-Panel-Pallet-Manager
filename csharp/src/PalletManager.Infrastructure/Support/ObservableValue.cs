namespace PalletManager.Infrastructure.Support;

public sealed class ObservableValue<T> : IObservable<T>
{
    private readonly List<IObserver<T>> _observers = new();
    private T _value;

    public ObservableValue(T initialValue)
    {
        _value = initialValue;
    }

    public IDisposable Subscribe(IObserver<T> observer)
    {
        if (!_observers.Contains(observer))
        {
            _observers.Add(observer);
            observer.OnNext(_value);
        }

        return new Unsubscriber(_observers, observer);
    }

    public void Set(T value)
    {
        _value = value;
        foreach (var observer in _observers.ToArray())
        {
            observer.OnNext(value);
        }
    }

    private sealed class Unsubscriber : IDisposable
    {
        private readonly List<IObserver<T>> _observers;
        private readonly IObserver<T> _observer;

        public Unsubscriber(List<IObserver<T>> observers, IObserver<T> observer)
        {
            _observers = observers;
            _observer = observer;
        }

        public void Dispose()
        {
            if (_observers.Contains(_observer))
            {
                _observers.Remove(_observer);
            }
        }
    }
}
