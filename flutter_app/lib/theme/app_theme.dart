import 'package:flutter/material.dart';

class AppColors {
  static const background = Color(0xFFF3F6FA);
  static const backgroundDeep = Color(0xFFE8EEF6);
  static const surfaceTint = Color(0xFFF7FAFD);
  static const sidebar = Color(0xFFF6F9FD);
  static const glass = Color(0xF5FFFFFF);
  static const glassStrong = Color(0xFFFFFFFF);
  static const glassMuted = Color(0xFFF7FAFE);
  static const primary = Color(0xFF2563EB);
  static const primaryDark = Color(0xFF0F3A78);
  static const accent = Color(0xFF0F766E);
  static const accentSoft = Color(0xFFDDF7F0);
  static const text = Color(0xFF111827);
  static const muted = Color(0xFF526274);
  static const border = Color(0xFFD9E2EE);
  static const hairline = Color(0xFFC9D5E4);
  static const paleBlue = Color(0xFFEAF2FF);
  static const warmSurface = Color(0xFFFFFFFF);
  static const success = Color(0xFF16A34A);
  static const warning = Color(0xFFF59E0B);
  static const danger = Color(0xFFDC2626);
}

class WinCleanerTheme {
  static ThemeData light() {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: AppColors.background,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primary,
        primary: AppColors.primary,
        secondary: AppColors.accent,
        surface: AppColors.glassStrong,
      ),
      fontFamily: 'Segoe UI',
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w800,
          color: AppColors.text,
        ),
        titleLarge: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: AppColors.text,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: AppColors.text,
        ),
        bodyMedium: TextStyle(fontSize: 14, color: AppColors.muted),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: AppColors.glass,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.glassStrong,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.hairline),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xB8FFFFFF),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.hairline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.hairline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.4),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          minimumSize: const Size(44, 44),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primaryDark,
          side: const BorderSide(color: AppColors.hairline),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          minimumSize: const Size(44, 44),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryDark,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          minimumSize: const Size(44, 44),
        ),
      ),
    );
  }
}

class GlassPanel extends StatefulWidget {
  const GlassPanel({
    super.key,
    required this.child,
    this.width,
    this.height,
    this.padding,
    this.radius = 14,
    this.color = AppColors.glass,
    this.borderColor = AppColors.border,
    this.shadow = true,
  });

  final Widget child;
  final double? width;
  final double? height;
  final EdgeInsetsGeometry? padding;
  final double radius;
  final Color color;
  final Color borderColor;
  final bool shadow;

  @override
  State<GlassPanel> createState() => _GlassPanelState();
}

class _GlassPanelState extends State<GlassPanel> {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width,
      height: widget.height,
      decoration: BoxDecoration(
        color: widget.color,
        borderRadius: BorderRadius.circular(widget.radius),
        border: Border.all(color: widget.borderColor),
        boxShadow: widget.shadow
            ? const [
                BoxShadow(
                  color: Color(0x160F2A44),
                  blurRadius: 12,
                  offset: Offset(0, 8),
                ),
              ]
            : null,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(widget.radius),
        child: Stack(
          children: [
            const Positioned(
              left: 1,
              right: 1,
              top: 1,
              height: 1,
              child: ColoredBox(color: Color(0xCCFFFFFF)),
            ),
            Material(
              color: Colors.transparent,
              child: Padding(
                padding: widget.padding ?? EdgeInsets.zero,
                child: widget.child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class FeatureIcon extends StatelessWidget {
  const FeatureIcon({
    super.key,
    required this.icon,
    this.size = 52,
    this.iconSize = 24,
    this.primary = AppColors.primary,
    this.secondary = AppColors.accent,
    this.selected = false,
  });

  final IconData icon;
  final double size;
  final double iconSize;
  final Color primary;
  final Color secondary;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final foreground = selected ? Colors.white : primary;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: selected
            ? primary
            : Color.alphaBlend(primary.withValues(alpha: 0.08), Colors.white),
        border: Border.all(
          color: selected ? primary : AppColors.border,
        ),
        borderRadius: BorderRadius.circular(size >= 48 ? 14 : 10),
      ),
      child: Center(
        child: ExcludeSemantics(
          child: Icon(icon, color: foreground, size: iconSize),
        ),
      ),
    );
  }
}
