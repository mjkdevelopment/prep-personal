String formatCurrency(num value) {
  final fixed = value.toStringAsFixed(0);
  final buffer = StringBuffer();

  for (var index = 0; index < fixed.length; index++) {
    final reverseIndex = fixed.length - index;
    buffer.write(fixed[index]);
    if (reverseIndex > 1 && reverseIndex % 3 == 1) {
      buffer.write(',');
    }
  }

  return '\$${buffer.toString()}';
}