import 'package:flutter/material.dart';

class AppPaletteOption {
  const AppPaletteOption({
    required this.id,
    required this.name,
    required this.description,
    required this.ivory,
    required this.paper,
    required this.sand,
    required this.petrol,
    required this.emerald,
    required this.gold,
    required this.terracotta,
    required this.sky,
    required this.plum,
    required this.amber,
    required this.coral,
    required this.sage,
    required this.slate,
    required this.ink,
    required this.success,
    required this.warning,
    required this.danger,
  });

  final String id;
  final String name;
  final String description;
  final Color ivory;
  final Color paper;
  final Color sand;
  final Color petrol;
  final Color emerald;
  final Color gold;
  final Color terracotta;
  final Color sky;
  final Color plum;
  final Color amber;
  final Color coral;
  final Color sage;
  final Color slate;
  final Color ink;
  final Color success;
  final Color warning;
  final Color danger;
}

class AppPalettes {
  static const emeraldEditorial = AppPaletteOption(
    id: 'emerald_editorial',
    name: 'Emerald Editorial',
    description: 'Sobria, premium y cercana al tono editorial de Stitch.',
    ivory: Color(0xFFF8F4EC),
    paper: Color(0xFFFFFCF7),
    sand: Color(0xFFE9E1D4),
    petrol: Color(0xFF1D3C3C),
    emerald: Color(0xFF335F52),
    gold: Color(0xFFC29A4B),
    terracotta: Color(0xFFB26B52),
    sky: Color(0xFF7FA8B2),
    plum: Color(0xFF8576A8),
    amber: Color(0xFFD0A55E),
    coral: Color(0xFFD78363),
    sage: Color(0xFF8BA37B),
    slate: Color(0xFF57615D),
    ink: Color(0xFF1A1E1C),
    success: Color(0xFF527C60),
    warning: Color(0xFFA06B2A),
    danger: Color(0xFFA0504A),
  );

  static const oceanLedger = AppPaletteOption(
    id: 'ocean_ledger',
    name: 'Ocean Ledger',
    description: 'Mas fresca y ejecutiva, con azules profundos y acentos ambar.',
    ivory: Color(0xFFEEF6F7),
    paper: Color(0xFFFFFFFF),
    sand: Color(0xFFDCECF0),
    petrol: Color(0xFF163847),
    emerald: Color(0xFF3F7A8C),
    gold: Color(0xFFEFB64A),
    terracotta: Color(0xFFE57D64),
    sky: Color(0xFF6AA3B6),
    plum: Color(0xFF6B7CA6),
    amber: Color(0xFFF2C86A),
    coral: Color(0xFFEB8B6B),
    sage: Color(0xFF80A39E),
    slate: Color(0xFF637981),
    ink: Color(0xFF122128),
    success: Color(0xFF3E7B66),
    warning: Color(0xFFB17A22),
    danger: Color(0xFFD36552),
  );

  static const terracottaLuxe = AppPaletteOption(
    id: 'terracotta_luxe',
    name: 'Terracotta Luxe',
    description: 'Mas calida, humana y distintiva sin perder contraste.',
    ivory: Color(0xFFFBF1EB),
    paper: Color(0xFFFFFAF6),
    sand: Color(0xFFF0DED4),
    petrol: Color(0xFF6E3D31),
    emerald: Color(0xFF355F5F),
    gold: Color(0xFFD8B067),
    terracotta: Color(0xFFBA6C55),
    sky: Color(0xFF8AA4B1),
    plum: Color(0xFF8B6C87),
    amber: Color(0xFFE0BA72),
    coral: Color(0xFFD98968),
    sage: Color(0xFF8F9A75),
    slate: Color(0xFF80685F),
    ink: Color(0xFF2A1E1A),
    success: Color(0xFF5A7A65),
    warning: Color(0xFFB27C2E),
    danger: Color(0xFFC45B49),
  );

  static const sageSun = AppPaletteOption(
    id: 'sage_sun',
    name: 'Sage & Sun',
    description: 'Mas suave y cotidiana, luminosa sin verse plana.',
    ivory: Color(0xFFF3F3E7),
    paper: Color(0xFFFEFDF9),
    sand: Color(0xFFE5E7D2),
    petrol: Color(0xFF50664F),
    emerald: Color(0xFF8EA16E),
    gold: Color(0xFFEDC85E),
    terracotta: Color(0xFFD98658),
    sky: Color(0xFF88AFBF),
    plum: Color(0xFF8C7CA7),
    amber: Color(0xFFF0D37D),
    coral: Color(0xFFE29774),
    sage: Color(0xFFA0B27E),
    slate: Color(0xFF687063),
    ink: Color(0xFF21261D),
    success: Color(0xFF67825B),
    warning: Color(0xFFBF8C2E),
    danger: Color(0xFFC9674F),
  );

  static const plumFinance = AppPaletteOption(
    id: 'plum_finance',
    name: 'Plum Finance',
    description: 'Mas moderna y fashion, con un violeta contenido y metalizados suaves.',
    ivory: Color(0xFFF4F0F6),
    paper: Color(0xFFFFFDFD),
    sand: Color(0xFFE5DDED),
    petrol: Color(0xFF46385D),
    emerald: Color(0xFF7B6D98),
    gold: Color(0xFFD8B06A),
    terracotta: Color(0xFF47908B),
    sky: Color(0xFF8DA6C9),
    plum: Color(0xFF8A72AE),
    amber: Color(0xFFE0BE81),
    coral: Color(0xFFCC8669),
    sage: Color(0xFF92A58F),
    slate: Color(0xFF6F6676),
    ink: Color(0xFF241D2B),
    success: Color(0xFF5F877B),
    warning: Color(0xFFB28635),
    danger: Color(0xFFC16D60),
  );

  static const all = [
    emeraldEditorial,
    oceanLedger,
    terracottaLuxe,
    sageSun,
    plumFinance,
  ];

  static AppPaletteOption byId(String id) {
    for (final palette in all) {
      if (palette.id == id) {
        return palette;
      }
    }

    return emeraldEditorial;
  }
}

class AppColors {
  static AppPaletteOption _palette = AppPalettes.emeraldEditorial;

  static AppPaletteOption get palette => _palette;

  static void usePalette(AppPaletteOption palette) {
    _palette = palette;
  }

  static Color get ivory => _palette.ivory;
  static Color get paper => _palette.paper;
  static Color get sand => _palette.sand;
  static Color get petrol => _palette.petrol;
  static Color get emerald => _palette.emerald;
  static Color get gold => _palette.gold;
  static Color get terracotta => _palette.terracotta;
  static Color get sky => _palette.sky;
  static Color get plum => _palette.plum;
  static Color get amber => _palette.amber;
  static Color get coral => _palette.coral;
  static Color get sage => _palette.sage;
  static Color get slate => _palette.slate;
  static Color get ink => _palette.ink;
  static Color get success => _palette.success;
  static Color get warning => _palette.warning;
  static Color get danger => _palette.danger;
}

class AppVisuals {
  static const categoryColorTokens = [
    'petrol',
    'emerald',
    'gold',
    'terracotta',
    'sky',
    'plum',
    'amber',
    'coral',
    'sage',
  ];

  static const categoryIconTokens = [
    'home',
    'bolt',
    'water',
    'tv',
    'school',
    'restaurant',
    'commute',
    'group',
    'favorite',
    'savings',
    'trending',
    'receipt',
    'work',
    'briefcase',
    'redeem',
    'account_balance',
    'paid',
    'apartment',
    'credit_card',
    'movie',
    'health',
  ];

  static Color colorFromToken(String token) {
    return switch (token) {
      'petrol' => AppColors.petrol,
      'emerald' => AppColors.emerald,
      'gold' => AppColors.gold,
      'terracotta' => AppColors.terracotta,
      'sky' => AppColors.sky,
      'plum' => AppColors.plum,
      'amber' => AppColors.amber,
      'coral' => AppColors.coral,
      'sage' => AppColors.sage,
      _ => AppColors.gold,
    };
  }

  static IconData iconFromToken(String token) {
    return switch (token) {
      'home' => Icons.home_rounded,
      'bolt' => Icons.bolt_rounded,
      'water' => Icons.water_drop_rounded,
      'tv' => Icons.live_tv_rounded,
      'school' => Icons.school_rounded,
      'restaurant' => Icons.restaurant_rounded,
      'commute' => Icons.commute_rounded,
      'group' => Icons.group_rounded,
      'favorite' => Icons.favorite_rounded,
      'savings' => Icons.savings_rounded,
      'trending' => Icons.trending_up_rounded,
      'receipt' => Icons.receipt_long_rounded,
      'work' => Icons.work_rounded,
      'briefcase' => Icons.business_center_rounded,
      'redeem' => Icons.redeem_rounded,
      'account_balance' => Icons.account_balance_rounded,
      'paid' => Icons.paid_rounded,
      'apartment' => Icons.apartment_rounded,
      'credit_card' => Icons.credit_card_rounded,
      'movie' => Icons.movie_rounded,
      'health' => Icons.health_and_safety_rounded,
      _ => Icons.category_rounded,
    };
  }
}

class AppTheme {
  static ThemeData themeForPalette(String paletteId) {
    AppColors.usePalette(AppPalettes.byId(paletteId));

    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.petrol,
      brightness: Brightness.light,
      surface: AppColors.paper,
    ).copyWith(
      primary: AppColors.petrol,
      secondary: AppColors.gold,
      tertiary: AppColors.emerald,
      surface: AppColors.paper,
      onSurface: AppColors.ink,
      outline: AppColors.sand,
      error: AppColors.danger,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.ivory,
      textTheme: TextTheme(
        displaySmall: TextStyle(
          fontSize: 34,
          fontWeight: FontWeight.w700,
          color: AppColors.ink,
          height: 1.1,
        ),
        headlineMedium: TextStyle(
          fontSize: 26,
          fontWeight: FontWeight.w700,
          color: AppColors.ink,
          height: 1.15,
        ),
        titleLarge: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: AppColors.ink,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: AppColors.ink,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: AppColors.ink,
          height: 1.5,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: AppColors.slate,
          height: 1.45,
        ),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
          color: AppColors.petrol,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.paper,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        margin: EdgeInsets.zero,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.paper,
        indicatorColor: AppColors.sand,
        height: 78,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final isSelected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 12,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
            color: isSelected ? AppColors.petrol : AppColors.slate,
          );
        }),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.paper,
        selectedColor: AppColors.sand,
        side: BorderSide(color: AppColors.sand),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        labelStyle: TextStyle(
          color: AppColors.ink,
          fontWeight: FontWeight.w600,
        ),
      ),
      dividerColor: AppColors.sand,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        labelStyle: TextStyle(color: AppColors.slate),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: AppColors.sand),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: AppColors.sand),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: AppColors.petrol, width: 1.4),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.petrol,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
    );
  }

  static ThemeData get lightTheme => themeForPalette(AppPalettes.emeraldEditorial.id);
}