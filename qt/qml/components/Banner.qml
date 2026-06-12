import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root

    property string code: "Y0S0"
    property string title: "Season"
    property url splashSource: ""
    property bool hasSplash: false
    property bool active: false

    signal activated()

    property int baseHeight: 210

    height: baseHeight
    clip: true

    Image {
        anchors.fill: parent
        visible: root.hasSplash
        source: root.splashSource
        fillMode: Image.PreserveAspectCrop
        sourceSize.width: 1920
        asynchronous: true
        cache: true
        scale: hover.hovered ? 1.06 : 1.0
        Behavior on scale { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        anchors.fill: parent
        visible: !root.hasSplash
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.gradient_top }
            GradientStop { position: 1.0; color: Theme.gradient_bottom }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
        opacity: hover.hovered ? 0.08 : 0.35
        Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 320
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Theme.scrim }
            GradientStop { position: 1.0; color: Theme.hero_shade_clear }
        }
    }

    Label {
        anchors.left: parent.left
        anchors.leftMargin: 32
        anchors.verticalCenter: parent.verticalCenter
        text: root.code
        color: Theme.text_primary
        font.pixelSize: 40
        font.weight: Font.ExtraBold
        font.letterSpacing: 1
    }

    Label {
        anchors.centerIn: parent
        text: root.title
        color: Theme.text_primary
        font.pixelSize: 40
        font.weight: Font.ExtraBold
        style: Text.Raised
        styleColor: Theme.text_shadow
    }

    Rectangle {
        visible: root.active
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.verticalCenter: parent.verticalCenter
        width: badgeLabel.implicitWidth + 20
        height: badgeLabel.implicitHeight + 10
        radius: Theme.radius_small
        color: Theme.scrim

        Label {
            id: badgeLabel
            anchors.centerIn: parent
            text: "DOWNLOADING"
            color: Theme.text_primary
            font.pixelSize: Theme.font_small
            font.bold: true
            font.letterSpacing: 2
        }
    }

    HoverHandler { id: hover }
    TapHandler { onTapped: root.activated() }
}
